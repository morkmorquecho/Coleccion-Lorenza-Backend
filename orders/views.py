from decimal import Decimal

import stripe
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import ValidationError
from rest_framework import status
from config import settings
from config.throttling import SensitiveOperationThrottle
from core.mixins import SentryErrorHandlerMixin, ViewSetSentryMixin
from core.permission import IsAdminOrReadOnly, IsOwner
from orders.docs.schemas import CANCEL_ORDER_VIEW, CHECKOUT_VIEW, ORDER_VIEWSET, SHIPPING_TRACKING_VIEWSET, STRIPE_WEBHOOK_VIEW
from orders.exceptions import OrderNotCancellableError, RefundError
from orders.filters import OrderFilter
from orders.serializer import CheckoutSerializer, OrderSerializer, ShippingTrackingSerializer
from orders.service import OrderService
from .models import CouponUsage, Order, OrderItem, Payment, ShippingTracking

stripe.api_key = settings.STRIPE_SECRET_KEY

@CHECKOUT_VIEW
class CheckoutView(SentryErrorHandlerMixin, APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SensitiveOperationThrottle]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            order, client_secret = OrderService.process_checkout(request.user, data)
        except ValidationError:
            raise
        except stripe.error.StripeError as e:
            self.logger.error(
                "Error de Stripe al crear PaymentIntent",
                extra={"user_id": request.user.id, "error": str(e)},
                exc_info=True
            )
            return Response(
                {'error': f'Error con el proveedor de pagos: {str(e)}'},
                status=status.HTTP_502_BAD_GATEWAY
            )

        self.logger.info(
            "Checkout iniciado",
            extra={
                "user_id": request.user.id,
                "order_id": order.id,
                "total": str(order.total),
            }
        )

        return Response({
            'order_id': order.id,
            'client_secret': client_secret,   # el frontend lo usa para mostrar el formulario de Stripe
            'publishable_key': settings.STRIPE_PUBLISHABLE_KEY
        }, status=status.HTTP_201_CREATED)

@STRIPE_WEBHOOK_VIEW
@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(SentryErrorHandlerMixin, APIView):
    """
    Stripe llama a este endpoint cuando un pago se completa o falla.
    No requiere autenticación porque viene de Stripe, pero se valida la firma.
    """
    permission_classes = [AllowAny]
    throttle_classes = [SensitiveOperationThrottle]

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        # Verificar que el evento realmente viene de Stripe
        try:
            event = stripe.Webhook.construct_event(...)
        except ValueError:
            self.logger.warning("Webhook payload inválido")
            return Response({'error': 'Payload inválido'}, status=400)
        except stripe.error.SignatureVerificationError:
            self.logger.warning("Firma de webhook inválida")
            return Response({'error': 'Firma inválida'}, status=400)
        
        self.logger.info("Webhook recibido", extra={"event_type": event['type']})

        event_type = event['type']

        if event_type == 'payment_intent.succeeded':
            OrderService.handle_payment_succeeded(event['data']['object'], logger=self.logger)

        elif event_type == 'payment_intent.payment_failed':
            OrderService.handle_payment_failed(event['data']['object'], logger=self.logger)
        
        elif event_type == 'payment_intent.canceled':
            OrderService.handle_payment_canceled(event['data']['object'], logger=self.logger)

        # Stripe espera un 200, si no reintenta el evento
        return Response({'status': 'ok'}, status=200)

@CANCEL_ORDER_VIEW
class CancelOrderView(SentryErrorHandlerMixin, APIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [SensitiveOperationThrottle]

    @transaction.atomic
    def post(self, request, pk):
        try:
            order = Order.objects.select_for_update().get(id=pk, user=request.user)
        except Order.DoesNotExist:
            return Response({'error': 'Orden no encontrada.'}, status=404)

        try:
            OrderService.cancel_order(order, logger=self.logger)
        except OrderNotCancellableError as e:
            return Response({'error': f'No se puede cancelar una orden en estado "{e}".'}, status=400)
        except RefundError as e:
            self.logger.error("Error al procesar reembolso", extra={"order_id": order.id, "error": str(e)}, exc_info=True)
            return Response({'error': f'Error al procesar el reembolso: {str(e)}'}, status=502)

        return Response({'message': 'Orden cancelada correctamente.'}, status=200)



@ORDER_VIEWSET
class OrderViewSet(ViewSetSentryMixin, ReadOnlyModelViewSet):
    queryset = Order.objects.prefetch_related(
        'items',
        'coupon_usage',
        'payments'
    ).select_related('user', 'address').order_by('-created_at')
    serializer_class = OrderSerializer
    permission_classes = [IsOwner]
    filterset_class = OrderFilter

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return Order.objects.none()
        
        return Order.objects.filter(user_id=user.id)

@SHIPPING_TRACKING_VIEWSET
class ShippingTrackingViewSet(ViewSetSentryMixin, ReadOnlyModelViewSet):
    serializer_class = ShippingTrackingSerializer 
    permission_classes = [IsOwner]

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return ShippingTracking.objects.none()
        
        return ShippingTracking.objects.filter(order__user_id=user.id)

