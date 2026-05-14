from decimal import Decimal
import logging
import json
from django.db import DatabaseError, transaction
from rest_framework.exceptions import ValidationError
import stripe

from core.mixins import SentryErrorHandlerMixin
from core.services.email_service import NewOrderEmail, OrderShippedEmail, SaleCompletedEmail
from orders.exceptions import OrderNotCancellableError, RefundError
from orders.models import CouponUsage, Order, OrderItem, Payment, ShippingTracking
from pieces.models import Piece
import requests
from django.core.cache import cache
from decouple import config


FRONTEND_URL=config('FRONTEND_URL')
BACKEND_URL=config('BACKEND_URL')
EMAIL_ADMIN=config('EMAIL_ADMIN')
class OrderService():
    @staticmethod
    @transaction.atomic
    def _create_order(user, data) -> tuple[Order, Payment]:
        """Solo toca la BD. Si algo falla, rollback limpio."""
        items_data = data['items']
        coupon = data.get('coupon_code')

        for item in items_data:
            piece = Piece.objects.select_for_update().get(id=item['piece'].id)
            if piece.quantity < item['quantity']:
                raise ValidationError(
                    {'items': f'Stock insuficiente para "{piece.title}". Disponible: {piece.quantity}'}
                )

        subtotal = sum( item['piece'].get_final_price('mx') * item['quantity'] for item in items_data)

        discount = Decimal('0')
        if coupon:
            discount = (subtotal * coupon.percentage / Decimal('100')).quantize(Decimal('0.01'))

        total = subtotal - discount

        order = Order.objects.create(
            user=user,
            address=data['address'],
            total=total,
            status='pending'
        )

        if coupon:
            CouponUsage.objects.create(
                order=order, coupon=coupon,
                user=user, discount_applied=discount
            )

        for item in items_data:
            piece = Piece.objects.select_for_update().get(id=item['piece'].id)
            OrderItem.objects.create(
                order=order, piece=piece,
                quantity=item['quantity'],
                price_snapshot=piece.get_final_price('mx')
            )
            piece.quantity -= item['quantity']
            piece.save()

        payment = Payment.objects.create(
            order=order,
            amount=total,
            payment_method=data['payment_method'],
            external_id='pending',
            status='pending'
        )

        return order, payment


    @staticmethod
    def _create_stripe_intent(order: Order, payment: Payment, coupon, discount) -> str:
        """Llama a Stripe FUERA del atomic. Si falla, la orden queda pending 
        pero la BD ya está commiteada y el webhook no puede llegar antes."""
        payment_intent = stripe.PaymentIntent.create(
            amount=int(payment.amount * 100),
            currency='mxn',
            payment_method_types=['card'],
            metadata={
                'order_id': str(order.id),
                'user_id': str(order.user_id),
                'coupon_code': coupon.code if coupon else '',
                'discount_applied': str(discount),
            }
        )

        payment.external_id = payment_intent['id']
        payment.save()  # Un solo save fuera del atomic, no hay riesgo

        return payment_intent['client_secret']


    @staticmethod
    def process_checkout(user, data) -> tuple[Order, str]:
        """Orquesta: primero BD (atomic), luego Stripe (fuera)."""
        order, payment = OrderService._create_order(user, data)

        client_secret = OrderService._create_stripe_intent(
            order, payment,
            coupon=data.get('coupon_code'),
            discount=payment.amount  # ya calculado dentro
        )

        return order, client_secret
    @staticmethod
    @transaction.atomic
    def handle_payment_succeeded(payment_intent: dict, logger=None) -> None:
        log = logger or logging.getLogger(__name__)

        try:
            payment = Payment.objects.select_for_update().get(
                external_id=payment_intent['id']
            )
        except Payment.DoesNotExist:
            # Retornar 404/500 para que Stripe reintente el webhook
            raise DatabaseError(f"Payment no encontrado: {payment_intent['id']}")

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
        SaleCompletedEmail.send_email(to_email=order.user.email,
                                    nombre=order.user.username 
                                    ,order_number=order.id, 
                                    order_date=order.created_at,
                                    order_total=order.total,
                                    order_url=f'{FRONTEND_URL}/cuenta')
        
        order_items = order.items.select_related('piece').all()

        NewOrderEmail.send_email(
            to_email=EMAIL_ADMIN,
            order_number=order.id,
            customer_name=order.user.username,
            customer_email=order.user.email,
            order_date=order.created_at,
            order_items=order_items,
            order_total=order.total,
            admin_order_url=f'{BACKEND_URL}/orders/order/',
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
            raise DatabaseError(f"Payment no encontrado: {payment_intent['id']}")

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
            raise DatabaseError(f"Payment no encontrado: {payment_intent['id']}")

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

        if not order.can_be_cancelled():  
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
                raise RefundError(str(e)) from e

        for item in order.items.all():  
            item.piece.release_stock(item.quantity)

        order.status = 'cancelled'
        order.save()

        if payment:
            payment.status = 'failed'
            payment.save()

        tracking = order.trakings.first()
        if tracking:
            if tracking.status == 'pending':
                tracking.status = 'cancelled'
                tracking.save()


    def update_tracking_number(instance: ShippingTracking, tracking_number: str) -> ShippingTracking:
        instance.tracking_number = tracking_number
        instance.save(update_fields=['tracking_number'])
        order_items = instance.order.items.select_related('pieces').all()

        OrderShippedEmail.send_email(
            to_email=instance.order.user.email,
            order_number=instance.order.id,
            order_date=instance.order.created_at,
            customer_name=instance.order.user.username,
            customer_email=instance.order.user.email,
            tracking_number=instance.tracking_number,
            tracking_url=instance.get_tracking_url,
            order_items=order_items,
        )
        return instance

