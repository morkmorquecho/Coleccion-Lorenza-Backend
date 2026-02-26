import stripe
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import ValidationError
from rest_framework import status
from config import settings
from orders.serializer import CheckoutSerializer
from .models import Order, OrderItem, Payment, ShippingTracking

stripe.api_key = settings.STRIPE_SECRET_KEY


class CheckoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = CheckoutSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        try:
            order, client_secret = self._process_checkout(request.user, data)
        except ValidationError:
            raise
        except stripe.error.StripeError as e:
            return Response(
                {'error': f'Error con el proveedor de pagos: {str(e)}'},
                status=status.HTTP_502_BAD_GATEWAY
            )

        return Response({
            'order_id': order.id,
            'client_secret': client_secret,   # el frontend lo usa para mostrar el formulario de Stripe
            'publishable_key': settings.STRIPE_PUBLISHABLE_KEY
        }, status=status.HTTP_201_CREATED)

    @transaction.atomic
    def _process_checkout(self, user, data):
        items_data = data['items']

        # 1. Validar stock
        for item in items_data:
            piece = item['piece']
            if piece.quantity < item['quantity']:
                raise ValidationError(
                    {'items': f'Stock insuficiente para "{piece.title}". Disponible: {piece.quantity}'}
                )

        # 2. Calcular total
        #pendiente a revisar
        total = sum(item['piece'].price_usa * item['quantity'] for item in items_data)

        # 3. Crear Order
        order = Order.objects.create(
            user=user,
            address=data['address'],
            total=total,
            status='pending'
        )

        # 4. Crear OrderItems y descontar stock
        for item in items_data:
            piece = item['piece']
            OrderItem.objects.create(
                order=order,
                piece=piece,
                quantity=item['quantity'],
                price_snapshot=piece.price
            )
            piece.stock -= item['quantity']
            piece.save()

        # 5. Crear Payment en pending
        payment = Payment.objects.create(
            order=order,
            amount=total,
            payment_method=data['payment_method'],
            external_id='pending',
            status='pending'
        )

        # 6. Crear intención de pago en Stripe
        # Esto va dentro del atomic pero al final, si falla hacemos rollback de todo
        payment_intent = stripe.PaymentIntent.create(
            amount=int(total * 100),  # Stripe trabaja en centavos
            currency='mxn',
            payment_method_types=['card'],
            metadata={
                'order_id': str(order.id),
                'user_id': str(user.id),
            }
        )

        # 7. Guardar el external_id que nos dio Stripe
        payment.external_id = payment_intent['id']
        payment.save()

        return order, payment_intent['client_secret']


@method_decorator(csrf_exempt, name='dispatch')
class StripeWebhookView(APIView):
    """
    Stripe llama a este endpoint cuando un pago se completa o falla.
    No requiere autenticación porque viene de Stripe, pero se valida la firma.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        payload = request.body
        sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')

        # Verificar que el evento realmente viene de Stripe
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
            )
        except ValueError:
            return Response({'error': 'Payload inválido'}, status=400)
        except stripe.error.SignatureVerificationError:
            return Response({'error': 'Firma inválida'}, status=400)

        event_type = event['type']

        if event_type == 'payment_intent.succeeded':
            self._handle_payment_succeeded(event['data']['object'])

        elif event_type == 'payment_intent.payment_failed':
            self._handle_payment_failed(event['data']['object'])

        # Stripe espera un 200, si no reintenta el evento
        return Response({'status': 'ok'}, status=200)

    @transaction.atomic
    def _handle_payment_succeeded(self, payment_intent):
        try:
            payment = Payment.objects.select_for_update().get(
                external_id=payment_intent['id']
            )
        except Payment.DoesNotExist:
            return

        if payment.status == 'completed':
            return  # ya fue procesado, Stripe a veces manda el evento dos veces

        payment.status = 'completed'
        payment.save()

        order = payment.order
        order.status = 'paid'
        order.save()

        # Recién aquí creamos el ShippingTracking porque el pago está confirmado
        ShippingTracking.objects.create(
            order=order,
            carrier='dhl',
            tracking_number='',  # lo asigna tu equipo logístico después
            status='pending'
        )

    @transaction.atomic
    def _handle_payment_failed(self, payment_intent):
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
        for item in order.orderitem_set.all():
            piece = item.piece
            piece.stock += item.quantity
            piece.save()