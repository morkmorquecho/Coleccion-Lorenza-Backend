from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter, OpenApiExample
from core.responses.messages import AuthMessages, UserMessages

_MODULE_PATH = 'users.views.'

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