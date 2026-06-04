from decimal import Decimal
import traceback

import stripe
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework.viewsets import ReadOnlyModelViewSet, ModelViewSet
from django.utils import timezone

from pieces.service import CurrencyService
from .models import Coupon
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
from orders.serializer import CheckoutSerializer, OrderSerializer, ShippingTrackingDetailSerializer, ShippingTrackingSerializer, UpdateTrackingNumberSerializer
from orders.service import OrderService
from .models import CouponUsage, Order, OrderItem, Payment, ShippingTracking
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAdminUser

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
    permission_classes = [AllowAny]
    throttle_classes = [SensitiveOperationThrottle]
    sentry_operation_name = "stripe_webhook"
    authentication_classes = [] 

    def post(self, request):
        return self.handle_with_sentry(
            operation=self._process_webhook,
            request=request,
            tags={'feature': 'webhook'},
        )

    def _process_webhook(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        try:
            event = stripe.Webhook.construct_event(
                payload,
                sig_header,
                settings.STRIPE_WEBHOOK_SECRET
            )
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
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ShippingTrackingDetailSerializer
        return ShippingTrackingSerializer

    def get_queryset(self):
        user = self.request.user
        if not user or not user.is_authenticated:
            return ShippingTracking.objects.none()

        if user.is_staff:
            return ShippingTracking.objects.all()

        return ShippingTracking.objects.filter(order__user_id=user.id)
    
    @action(
        detail=True,
        methods=['patch'],
        permission_classes=[IsAdminUser],
        url_path='update-tracking-number'
    )
    def update_tracking_number(self, request, pk=None):
        instance = self.get_object()
        serializer = UpdateTrackingNumberSerializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)

        updated = OrderService.update_tracking_number(
            instance=instance,
            tracking_number=serializer.validated_data['tracking_number']
        )

        return Response(UpdateTrackingNumberSerializer(updated).data)


class ValidateCouponView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        code = request.query_params.get('code', '').strip().upper()

        if not code:
            return Response(
                {'detail': 'El parámetro code es requerido.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            today = timezone.now().date()
            coupon = Coupon.objects.get(
                code=code,
                valid_from__lte=today,
                valid_until__gte=today
            )
        except Coupon.DoesNotExist:
            return Response(
                {'detail': 'Cupón no válido o expirado.'},
                status=status.HTTP_404_NOT_FOUND
            )

        return Response({'percentage': coupon.percentage})

class ExchangeRateView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request):
        rate = CurrencyService.get_usd_rate()
        return Response({'usd_to_mxn': rate})
    

# views.py (temporal, solo para debug)
from django.core.cache import cache
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
import time

class CacheDebugView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # 1. ¿Qué backend está usando Django?
        cache_backend = settings.CACHES.get('default', {})
        
        # 2. Prueba de escritura/lectura en Redis
        test_key = 'cache_debug_test'
        test_value = 'ok_from_redis'
        
        write_ok = False
        read_ok = False
        latency_ms = None

        try:
            cache.set(test_key, test_value, 30)
            write_ok = True

            t0 = time.monotonic()
            result = cache.get(test_key)
            latency_ms = round((time.monotonic() - t0) * 1000, 2)

            read_ok = result == test_value
        except Exception as e:
            error = str(e)
        else:
            error = None

        # 3. ¿El key del tipo de cambio ya existe?
        from pieces.service import EXCHANGE_RATE_CACHE_KEY  
        rate_cached = cache.get(EXCHANGE_RATE_CACHE_KEY)

        return Response({
            'backend': cache_backend.get('BACKEND', 'desconocido'),
            'location': cache_backend.get('LOCATION', 'N/A'),  # URL de Redis
            'write_ok': write_ok,
            'read_ok': read_ok,
            'latency_ms': latency_ms,
            'error': error,
            'exchange_rate_in_cache': rate_cached is not None,
            'exchange_rate_value': str(rate_cached) if rate_cached else None,
        })