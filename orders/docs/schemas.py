from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiResponse,
)
from drf_spectacular.types import OpenApiTypes

from orders.serializer import (
    CheckoutSerializer,
    OrderSerializer,
    ShippingTrackingSerializer,
)

_MODULE_PATH_ORDERS = "orders.views"

# ─────────────────────────────────────────────
# CHECKOUT
# ─────────────────────────────────────────────

CHECKOUT_VIEW = extend_schema(
    summary="Crear Checkout y generar intención de pago",
    tags=["orders - checkout"],
    description=(
        "Procesa el checkout completo de una orden.\n\n"
        "Valida stock, aplica cupones, crea la orden, items, pago en estado `pending` "
        "y genera una `PaymentIntent` en Stripe.\n\n"
        "El frontend debe usar `client_secret` para completar el pago con Stripe.\n\n"
        "Requiere autenticación.\n\n"
        f"**Code:** `{_MODULE_PATH_ORDERS}.CheckoutView_post`"
    ),
    request=CheckoutSerializer,
    responses={
        201: OpenApiResponse(
            description="Checkout creado correctamente.",
            response=OpenApiTypes.OBJECT,
        ),
        400: OpenApiResponse(description="Datos inválidos o stock insuficiente."),
        502: OpenApiResponse(description="Error con el proveedor de pagos."),
    },
)

# ─────────────────────────────────────────────
# STRIPE WEBHOOK
# ─────────────────────────────────────────────

STRIPE_WEBHOOK_VIEW = extend_schema(
    summary="Webhook de Stripe",
    tags=["orders - payments"],
    description=(
        "Endpoint utilizado por Stripe para notificar eventos de pago.\n\n"
        "Valida la firma del webhook y procesa los siguientes eventos:\n"
        "- `payment_intent.succeeded`\n"
        "- `payment_intent.payment_failed`\n"
        "- `payment_intent.canceled`\n\n"
        "Actualiza el estado del `Payment`, la `Order` y crea o revierte "
        "`ShippingTracking` según corresponda.\n\n"
        "No requiere autenticación (Stripe only).\n\n"
        f"**Code:** `{_MODULE_PATH_ORDERS}.StripeWebhookView_post`"
    ),
    responses={
        200: OpenApiResponse(description="Evento procesado correctamente."),
        400: OpenApiResponse(description="Payload o firma inválida."),
    },
)

# ─────────────────────────────────────────────
# CANCEL ORDER
# ─────────────────────────────────────────────

CANCEL_ORDER_VIEW = extend_schema(
    summary="Cancelar una Orden",
    tags=["orders"],
    description=(
        "Cancela una orden perteneciente al usuario autenticado.\n\n"
        "Comportamiento según estado:\n"
        "- `pending`: cancela la PaymentIntent en Stripe.\n"
        "- `paid`: genera un reembolso en Stripe.\n\n"
        "Revierte stock, actualiza estados y elimina el `ShippingTracking` "
        "si aún está pendiente.\n\n"
        "Requiere autenticación y ser dueño de la orden.\n\n"
        f"**Code:** `{_MODULE_PATH_ORDERS}.CancelOrderView_post`"
    ),
    responses={
        200: OpenApiResponse(description="Orden cancelada correctamente."),
        400: OpenApiResponse(description="La orden no puede cancelarse."),
        404: OpenApiResponse(description="Orden no encontrada."),
        502: OpenApiResponse(description="Error al procesar el reembolso."),
    },
)

# ─────────────────────────────────────────────
# ORDER
# ─────────────────────────────────────────────

ORDER_VIEWSET = extend_schema_view(
    list=extend_schema(
        summary="Listar Órdenes del Usuario",
        tags=["orders"],
        description=(
            "Retorna el listado de órdenes pertenecientes al usuario autenticado.\n\n"
            "Incluye items, pagos y uso de cupones.\n\n"
            "Soporta filtros vía `OrderFilter`.\n\n"
            "Requiere autenticación.\n\n"
            f"**Code:** `{_MODULE_PATH_ORDERS}.OrderViewSet_list`"
        ),
        responses={200: OrderSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Obtener Detalle de una Orden",
        tags=["orders"],
        description=(
            "Retorna el detalle completo de una orden específica.\n\n"
            "Solo el propietario puede acceder.\n\n"
            "Requiere autenticación.\n\n"
            f"**Code:** `{_MODULE_PATH_ORDERS}.OrderViewSet_retrieve`"
        ),
        responses={
            200: OrderSerializer,
            404: OpenApiResponse(description="Orden no encontrada."),
        },
    ),
)

# ─────────────────────────────────────────────
# SHIPPING TRACKING
# ─────────────────────────────────────────────

SHIPPING_TRACKING_VIEWSET = extend_schema_view(
    list=extend_schema(
        summary="Listar Tracking de Envíos",
        tags=["orders - shipping"],
        description=(
            "Retorna los registros de seguimiento de envío asociados "
            "a las órdenes del usuario.\n\n"
            "Solo se crean cuando el pago fue confirmado.\n\n"
            "Requiere autenticación.\n\n"
            f"**Code:** `{_MODULE_PATH_ORDERS}.ShippingTrackingViewSet_list`"
        ),
        responses={200: ShippingTrackingSerializer(many=True)},
    ),
    retrieve=extend_schema(
        summary="Obtener Tracking de Envío",
        tags=["orders - shipping"],
        description=(
            "Retorna el detalle de un seguimiento de envío específico.\n\n"
            "Solo el propietario puede acceder.\n\n"
            "Requiere autenticación.\n\n"
            f"**Code:** `{_MODULE_PATH_ORDERS}.ShippingTrackingViewSet_retrieve`"
        ),
        responses={
            200: ShippingTrackingSerializer,
            404: OpenApiResponse(description="Tracking no encontrado."),
        },
    ),
)