from django.utils import timezone
from decimal import Decimal
import logging
import json
from django.db import DatabaseError, transaction
from rest_framework.exceptions import ValidationError
import stripe

from core.mixins import SentryErrorHandlerMixin
from core.services.email_service import (
    OrderCancelledAdminEmail, OrderCancelledUserEmail,
    OrderCreatedAdminEmail, OrderShippedEmail, OrderCreatedUserEmail
)
from orders.exceptions import OrderNotCancellableError, RefundError
from orders.models import CouponUsage, Order, OrderItem, Payment, ShippingTracking
from pieces.models import Piece
from django.core.cache import cache
from decouple import config


FRONTEND_URL = config('FRONTEND_URL')
BACKEND_URL = config('BACKEND_URL')
EMAIL_ADMIN = config('EMAIL_ADMIN')


class OrderService():

    # ─────────────────────────────────────────────
    # HELPERS INTERNOS
    # ─────────────────────────────────────────────

    @staticmethod
    def _expire_previous_pending_orders(user) -> None:
        """
        Antes de crear un nuevo pedido, expira todos los pedidos pendientes
        del usuario. El stock nunca fue descontado en pending, así que no
        hay nada que devolver — solo marcamos como expirado y cancelamos
        el PaymentIntent en Stripe si existe.
        """
        stale_orders = Order.objects.filter(
            user=user,
            status='pending'
        ).prefetch_related('payments')

        for order in stale_orders:
            payment = order.payments.first()

            if payment and payment.external_id != 'pending':
                try:
                    stripe.PaymentIntent.cancel(payment.external_id)
                except stripe.error.InvalidRequestError:
                    # Ya estaba cancelado en Stripe, no importa
                    pass

            order.status = 'expired'
            order.save(update_fields=['status'])

            if payment:
                payment.status = 'failed'
                payment.save(update_fields=['status'])

    @staticmethod
    def _validate_stock(items_data) -> None:
        """
        Validación optimista de stock antes de llamar a Stripe.
        No usa lock — su propósito es UX (evitar que el usuario
        llegue a Stripe si ya no hay stock visible).
        La garantía real contra overselling está en handle_payment_succeeded.
        """
        for item in items_data:
            piece = item['piece']
            if piece.quantity < item['quantity']:
                raise ValidationError({
                    'items': f'Stock insuficiente para "{piece.title}". '
                             f'Disponible: {piece.quantity}'
                })

    # ─────────────────────────────────────────────
    # CREACIÓN DE PEDIDO
    # ─────────────────────────────────────────────


    @staticmethod
    @transaction.atomic
    def _create_order(user, data) -> tuple[Order, Payment, Decimal]: 
        items_data = data['items']
        coupon = data.get('coupon_code')

        subtotal = sum(
            item['piece'].get_final_price('mx') * item['quantity']
            for item in items_data
        )

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
            OrderItem.objects.create(
                order=order,
                piece=item['piece'],
                quantity=item['quantity'],
                price_snapshot=item['piece'].get_final_price('mx')
            )

        payment = Payment.objects.create(
            order=order,
            amount=total,
            payment_method=data['payment_method'],
            external_id='pending',
            status='pending'
        )

        return order, payment, discount  

    @staticmethod
    def _create_stripe_intent(order: Order, payment: Payment, coupon, discount) -> str:
        """
        Llama a Stripe FUERA del atomic para no mantener locks de BD
        durante una llamada HTTP externa.
        """
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
        payment.save(update_fields=['external_id'])

        return payment_intent['client_secret']

    @staticmethod
    def process_checkout(user, data) -> tuple[Order, str]:
        """
        Orquesta el flujo completo:
        1. Expira pedidos pendientes anteriores
        2. Valida stock (optimista, para UX)
        3. Crea orden en BD (sin descontar stock)
        4. Llama a Stripe fuera del atomic
        """
        OrderService._expire_previous_pending_orders(user)
        OrderService._validate_stock(data['items'])

        order, payment, discount = OrderService._create_order(user, data)  # ← desempaca discount

        client_secret = OrderService._create_stripe_intent(
            order, payment,
            coupon=data.get('coupon_code'),
            discount=discount  # ← ahora sí es el descuento real
        )

        return order, client_secret

    # ─────────────────────────────────────────────
    # WEBHOOKS DE STRIPE
    # ─────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def handle_payment_succeeded(payment_intent: dict, logger=None) -> None:
        log = logger or logging.getLogger(__name__)

        try:
            payment = Payment.objects.select_for_update().get(
                external_id=payment_intent['id']
            )
        except Payment.DoesNotExist:
            raise DatabaseError(f"Payment no encontrado: {payment_intent['id']}")

        if payment.status == 'completed':
            log.warning(
                f"Evento de pago duplicado ignorado\n"
                f"{json.dumps({'payment_intent_id': payment_intent['id']}, indent=2)}"
            )
            return

        order = payment.order

        # Adquirir lock en las piezas ordenadas por ID para evitar deadlocks
        items = list(
            order.items.select_related('piece')
            .select_for_update()
            .order_by('piece_id')
        )

        # Validar stock real con el lock ya adquirido
        # Esta es la garantía real contra overselling
        for item in items:
            if item.piece.quantity < item.quantity:
                log.error(
                    f"Overselling detectado — reembolsando automáticamente\n"
                    f"{json.dumps({'order_id': order.id, 'piece_id': item.piece.id, 'piece_title': item.piece.title, 'stock_disponible': item.piece.quantity, 'cantidad_solicitada': item.quantity}, indent=2)}"
                )
                try:
                    stripe.Refund.create(
                        payment_intent=payment.external_id,
                        reason='requested_by_customer'
                    )
                except stripe.error.StripeError as e:
                    log.error(f"Error al reembolsar overselling: {e}")

                payment.status = 'failed'
                payment.save(update_fields=['status'])
                order.status = 'cancelled'
                order.save(update_fields=['status'])
                return  # Retornar 200 a Stripe para que no reintente

        # Stock validado — descontar definitivamente
        for item in items:
            item.piece.quantity -= item.quantity
            item.piece.save(update_fields=['quantity'])

        payment.status = 'completed'
        payment.save(update_fields=['status'])

        order.status = 'paid'
        order.save(update_fields=['status'])

        ShippingTracking.objects.create(order=order)

        OrderCreatedUserEmail.send_email(
            to_email=order.user.email,
            nombre=order.user.username,
            order_number=order.id,
            order_date=order.created_at,
            order_total=order.total,
            order_url=f'{FRONTEND_URL}/cuenta'
        )

        order_items = order.items.select_related('piece').all()

        OrderCreatedAdminEmail.send_email(
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
        """
        El stock nunca fue descontado en pending,
        solo marcamos el pago y la orden como fallidos.
        """
        log = logger or logging.getLogger(__name__)

        try:
            payment = Payment.objects.select_for_update().get(
                external_id=payment_intent['id']
            )
        except Payment.DoesNotExist:
            raise DatabaseError(f"Payment no encontrado: {payment_intent['id']}")

        if payment.status == 'failed':
            return  # Ya fue procesado

        payment.status = 'failed'
        payment.save(update_fields=['status'])

        order = payment.order
        order.status = 'cancelled'
        order.save(update_fields=['status'])

        log.info(
            f"Pago cancelado\n"
            f"{json.dumps({'payment_intent_id': payment_intent['id'], 'order_id': order.id}, indent=2)}"
        )

    @staticmethod
    @transaction.atomic
    def handle_payment_failed(payment_intent: dict, logger=None) -> None:
        """
        El stock nunca fue descontado en pending,
        solo marcamos el pago y la orden como fallidos.
        """
        log = logger or logging.getLogger(__name__)

        try:
            payment = Payment.objects.select_for_update().get(
                external_id=payment_intent['id']
            )
        except Payment.DoesNotExist:
            raise DatabaseError(f"Payment no encontrado: {payment_intent['id']}")

        if payment.status == 'failed':
            return  # Ya fue procesado

        payment.status = 'failed'
        payment.save(update_fields=['status'])

        order = payment.order
        order.status = 'cancelled'
        order.save(update_fields=['status'])

        log.warning(
            f"Pago fallido\n"
            f"{json.dumps({'order_id': order.id, 'payment_intent_id': payment_intent['id'], 'failure_reason': payment_intent.get('last_payment_error', {}).get('message')}, indent=2)}"
        )

    # ─────────────────────────────────────────────
    # CANCELACIÓN MANUAL
    # ─────────────────────────────────────────────

    @staticmethod
    @transaction.atomic
    def cancel_order(order: Order, logger=None) -> None:
        log = logger or logging.getLogger(__name__)

        if not order.can_be_cancelled():
            raise OrderNotCancellableError(order.status)

        payment = order.payments.first()

        if order.status == 'pending':
            # Stock nunca fue descontado, solo cancelar el PaymentIntent
            try:
                if payment and payment.external_id != 'pending':
                    stripe.PaymentIntent.cancel(payment.external_id)
            except stripe.error.InvalidRequestError:
                pass

        elif order.status == 'paid':
            # Stock sí fue descontado — devolver
            for item in order.items.select_related('piece').all():
                item.piece.quantity += item.quantity
                item.piece.save(update_fields=['quantity'])

            # Reembolsar en Stripe
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

        order.status = 'cancelled'
        order.save(update_fields=['status'])

        if payment:
            payment.status = 'failed'
            payment.save(update_fields=['status'])

        tracking = order.trakings.first()
        if tracking and tracking.status == 'pending':
            tracking.status = 'cancelled'
            tracking.save(update_fields=['status'])

        order_items = order.items.select_related('piece').all()

        OrderCancelledUserEmail.send_email(
            to_email=order.user.email,
            customer_name=order.user.username,
            order_number=order.id,
            cancellation_date=timezone.now().date(),
            order_items=order_items,
            order_total=order.total,
            shop_url=FRONTEND_URL
        )

        OrderCancelledAdminEmail.send_email(
            to_email=EMAIL_ADMIN,
            customer_name=order.user.username,
            order_number=order.id,
            cancellation_date=timezone.now().date(),
            order_items=order_items,
            order_total=order.total,
            customer_email=order.user.email,
            customer_phone=order.address.phone_number,
            admin_order_url=BACKEND_URL
        )

    # ─────────────────────────────────────────────
    # TRACKING
    # ─────────────────────────────────────────────

    @staticmethod
    def update_tracking_number(instance: ShippingTracking, tracking_number: str) -> ShippingTracking:
        instance.tracking_number = tracking_number
        instance.status = 'shipped'
        instance.save(update_fields=['tracking_number', 'status'])

        order_items = instance.order.items.select_related('piece').all()

        OrderShippedEmail.send_email(
            to_email=instance.order.user.email,
            order_number=instance.order.id,
            order_date=instance.order.created_at,
            customer_name=instance.order.user.username,
            customer_email=instance.order.user.email,
            tracking_number=instance.tracking_number,
            tracking_url=instance.get_tracking_url(),
            order_items=order_items,
            order_total=instance.order.total
        )
        return instance