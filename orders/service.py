from decimal import Decimal
import logging
import json
from django.db import transaction
from rest_framework.exceptions import ValidationError
import stripe

from core.mixins import SentryErrorHandlerMixin
from orders.exceptions import OrderNotCancellableError, RefundError
from orders.models import CouponUsage, Order, OrderItem, Payment, ShippingTracking

class OrderService():
    @staticmethod
    @transaction.atomic
    def process_checkout(user, data) -> tuple[Order, str]:
        items_data = data['items']
        coupon = data.get('coupon_code') 

        # 1. Validar stock
        for item in items_data:
            piece = item['piece']
            if piece.quantity < item['quantity']:
                raise ValidationError(
                    {'items': f'Stock insuficiente para "{piece.title}". Disponible: {piece.quantity}'}
                )

        # 2. Calcular total
        subtotal = sum(item['piece'].get_final_price('mx') * item['quantity'] for item in items_data)

        # 3. Aplicar descuento si hay cupón
        discount = Decimal('0')
        if coupon:
            discount = (subtotal * coupon.percentage / Decimal('100')).quantize(Decimal('0.01'))

        total = subtotal - discount

        # 4. Crear Order
        order = Order.objects.create(
            user=user,
            address=data['address'],
            total=total,
            status='pending'
        )

        # 5. Registrar uso del cupón
        if coupon:
            CouponUsage.objects.create(
                order=order,
                coupon=coupon,
                user=user,
                discount_applied=discount
            )

        # 6. Crear OrderItems y descontar stock
        for item in items_data:
            piece = item['piece']
            OrderItem.objects.create(
                order=order,
                piece=piece,
                quantity=item['quantity'],
                price_snapshot=piece.get_final_price('mx')
            )
            piece.quantity -= item['quantity']
            piece.save()

        # 7. Crear Payment en pending
        payment = Payment.objects.create(
            order=order,
            amount=total,
            payment_method=data['payment_method'],
            external_id='pending',
            status='pending'
        )

        # 8. Crear intención de pago en Stripe
        payment_intent = stripe.PaymentIntent.create(
            amount=int(total * 100),
            currency='mxn',
            payment_method_types=['card'],
            metadata={
                'order_id': str(order.id),
                'user_id': str(user.id),
                'coupon_code': coupon.code if coupon else '',
                'discount_applied': str(discount),
            }
        )

        # 9. Guardar el external_id que nos dio Stripe
        payment.external_id = payment_intent['id']
        payment.save()

        return order, payment_intent['client_secret']        

    @staticmethod
    @transaction.atomic
    def handle_payment_succeeded(payment_intent: dict, logger=None) -> None:
        log = logger or logging.getLogger(__name__)

        try:
            payment = Payment.objects.select_for_update().get(
                external_id=payment_intent['id']
            )
        except Payment.DoesNotExist:
            return

        if payment.status == 'completed':
            log.warning(
                        f"Evento de pago duplicado ignorado\n"
                        f"{json.dumps({'payment_intent_id': payment_intent['id']}, indent=2)}"
            )
            return  

        payment.status = 'completed'
        payment.save()

        order = payment.order
        order.status = 'paid'
        order.save()

        # Recién aquí creamos el ShippingTracking porque el pago está confirmado
        ShippingTracking.objects.create(
            order=order,
        )

        log.info(
            f"Pago completado\n"
            f"{json.dumps({'order_id': order.id, 'payment_intent_id': payment_intent['id'], 'amount': str(payment.amount)}, indent=2)}"
        )

    @staticmethod
    @transaction.atomic
    def handle_payment_canceled(payment_intent: dict, logger=None) -> None:
        log = logger or logging.getLogger(__name__)

        try:
            payment = Payment.objects.select_for_update().get(
                external_id=payment_intent['id']
            )
        except Payment.DoesNotExist:
            return

        if payment.status == 'failed':
            return  # ya fue procesado


        payment.status = 'failed'
        payment.save()

        order = payment.order
        order.status = 'cancelled'
        order.save()

        for item in order.items.all():
            piece = item.piece
            piece.quantity += item.quantity 
            piece.save()

        log.info(
            f"Pago cancelado\n"
            f"{json.dumps({'payment_intent_id': payment_intent['id'], 'order_id': order.id}, indent=2)}"
        )
    @staticmethod
    @transaction.atomic
    def handle_payment_failed(payment_intent: dict, logger=None) -> None:
        log = logger or logging.getLogger(__name__)
        try:
            payment = Payment.objects.select_for_update().get(
                external_id=payment_intent['id']
            )
        except Payment.DoesNotExist:
            return

        payment.status = 'failed'
        payment.save()

        order = payment.order
        order.status = 'cancelled'
        order.save()

        # Devolver stock
        for item in order.items.all():
            piece = item.piece
            piece.quantity += item.quantity
            piece.save()

        log.warning(
            f"Pago fallido\n"
            f"{json.dumps({'order_id': order.id, 'payment_intent_id': payment_intent['id'], 'failure_reason': payment_intent.get('last_payment_error', {}).get('message')}, indent=2)}"
        )

    @staticmethod
    @transaction.atomic
    def cancel_order(order: Order, logger=None) -> None:
        log = logger or logging.getLogger(__name__)

        if order.status in ['shipped', 'cancelled']:
            raise OrderNotCancellableError(order.status)

        payment = order.payments.first()

        if order.status == 'pending':
            try:
                if payment and payment.external_id != 'pending':
                    stripe.PaymentIntent.cancel(payment.external_id)
            except stripe.error.InvalidRequestError:
                pass

        elif order.status == 'paid':
            try:
                stripe.Refund.create(
                    payment_intent=payment.external_id,
                    reason='requested_by_customer'
                )

                log.info(
                    f"Reembolso creado\n"
                    f"{json.dumps({'order_id': order.id, 'amount': str(payment.amount)}, indent=2)}"
                )
            except stripe.error.StripeError as e:
                raise RefundError(str(e)) from e  #  envuelves el error de Stripe en tu propio error

        for item in order.items.all():
            piece = item.piece
            piece.quantity += item.quantity
            piece.save()

        order.status = 'cancelled'
        order.save()

        if payment:
            payment.status = 'failed'
            payment.save()

        tracking = order.trakings.first()
        if tracking and tracking.status == 'pending':
            tracking.delete()