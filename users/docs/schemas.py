

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter, OpenApiExample, extend_schema_view
from auth.docs.request import GOOGLE_LOGIN_REQUEST, RESEND_CONFIRMATION_EMAIL_REQUEST
from auth.docs.response import LOGIN_RESPONSE
from core.responses.messages import AuthMessages, UserMessages
from core.responses.schemas import UserResponses
from ..serializers import AddressSerializer
_MODULE_PATH = 'auth.views' 

EMAIL_UPDATE = extend_schema(
    summary="Modificar Correo",
    tags=["users"],
    description=(
        "Se solicita la actualizacion del correo electronico del usuario\n\n"
        "Se envía un correo de verificación para actualizar el nuevo correo, este correo llega el nuevo correo\n\n"
        "Accesible para usuarios autenticados\n\n"
        f"**Code:** `{_MODULE_PATH}.UserViewSet_post`"
    ),
    responses={
        201: OpenApiResponse(description=UserMessages.EMAIL_SENT_IF_EXISTS),
    }
)

ADDRESS_VIEWSET = extend_schema_view(
    list=extend_schema(
        summary="Listar Direcciones",
        tags=["users"],
        description=(
            "Retorna todas las direcciones registradas del usuario autenticado.\n\n"
            "Los resultados se ordenan primero por dirección predeterminada y luego por fecha de creación (más reciente primero).\n\n"
            "Accesible para usuarios autenticados.\n\n"
            f"**Code:** `{_MODULE_PATH}.AddressViewSet_list`"
        ),
        responses={
            200: AddressSerializer,
        }
    ),
    retrieve=extend_schema(
        summary="Obtener Dirección",
        tags=["users"],
        description=(
            "Retorna el detalle de una dirección específica del usuario autenticado.\n\n"
            "Solo el propietario de la dirección puede acceder a este recurso.\n\n"
            "Accesible para usuarios autenticados.\n\n"
            f"**Code:** `{_MODULE_PATH}.AddressViewSet_retrieve`"
        ),
        responses={
            200: AddressSerializer,
            404: OpenApiResponse(description="Dirección no encontrada."),
        }
    ),
    create=extend_schema(
        summary="Crear Dirección",
        tags=["users"],
        description=(
            "Crea una nueva dirección para el usuario autenticado.\n\n"
            "Si `is_default` es `true`, cualquier dirección predeterminada existente será reemplazada automáticamente.\n\n"
            "El campo `user` se asigna automáticamente al usuario autenticado.\n\n"
            "Accesible para usuarios autenticados.\n\n"
            f"**Code:** `{_MODULE_PATH}.AddressViewSet_create`"
        ),
        responses={
            201: AddressSerializer,
            400: OpenApiResponse(description="Datos inválidos o ya existe una dirección predeterminada."),
        }
    ),
    update=extend_schema(
        summary="Actualizar Dirección",
        tags=["users"],
        description=(
            "Actualiza todos los campos de una dirección existente del usuario autenticado.\n\n"
            "Si `is_default` es `true`, la dirección predeterminada anterior será reemplazada automáticamente.\n\n"
            "Solo el propietario de la dirección puede modificarla.\n\n"
            "Accesible para usuarios autenticados.\n\n"
            f"**Code:** `{_MODULE_PATH}.AddressViewSet_update`"
        ),
        responses={
            200: AddressSerializer,
            400: OpenApiResponse(description="Datos inválidos o ya existe una dirección predeterminada."),
            404: OpenApiResponse(description="Dirección no encontrada."),
        }
    ),
    partial_update=extend_schema(
        summary="Actualizar Dirección Parcialmente",
        tags=["users"],
        description=(
            "Actualiza uno o más campos de una dirección existente del usuario autenticado.\n\n"
            "Si `is_default` es `true`, la dirección predeterminada anterior será reemplazada automáticamente.\n\n"
            "Solo el propietario de la dirección puede modificarla.\n\n"
            "Accesible para usuarios autenticados.\n\n"
            f"**Code:** `{_MODULE_PATH}.AddressViewSet_partial_update`"
        ),
        responses={
            200: AddressSerializer,
            400: OpenApiResponse(description="Datos inválidos o ya existe una dirección predeterminada."),
            404: OpenApiResponse(description="Dirección no encontrada."),
        }
    ),
    destroy=extend_schema(
        summary="Eliminar Dirección",
        tags=["users"],
        description=(
            "Elimina una dirección del usuario autenticado.\n\n"
            "Solo el propietario de la dirección puede eliminarla.\n\n"
            "Accesible para usuarios autenticados.\n\n"
            f"**Code:** `{_MODULE_PATH}.AddressViewSet_destroy`"
        ),
        responses={
            204: OpenApiResponse(description="Dirección eliminada correctamente."),
            404: OpenApiResponse(description="Dirección no encontrada."),
        }
    ),
)

ADDRESS_SET_DEFAULT = extend_schema(
    summary="Establecer Dirección Predeterminada",
    tags=["users"],
    description=(
        "Marca una dirección específica como predeterminada del usuario autenticado.\n\n"
        "Cualquier dirección que previamente tuviera `is_default=true` será desactivada automáticamente.\n\n"
        "Solo el propietario de la dirección puede ejecutar esta acción.\n\n"
        "Accesible para usuarios autenticados.\n\n"
        f"**Code:** `{_MODULE_PATH}.AddressViewSet_set_default`"
    ),
    responses={
        200: AddressSerializer,
        404: OpenApiResponse(description="Dirección no encontrada."),
    }
)