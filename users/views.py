from django.shortcuts import render
from rest_framework.generics import UpdateAPIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from core.mixins import IsOwner, SentryErrorHandlerMixin
from users.serializers import EmailUpdateSerializer
from auth.services import UsersRegisterService
from core.services.email_service import ConfirmUserEmail,UpdateUserEmail
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework import viewsets, status
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse

_MODULE_PATH = __name__

User = get_user_model()

@extend_schema(
    summary="Modificar Correo",
    tags=["user"],
    description=(
        "Se solicita la actualizacion del correo electronico del usuario\n\n"
        "Se envía un correo de verificación para actualizar el nuevo correo, este correo llega el nuevo correo\n\n"
        "Accesible para usuarios autenticados\n\n"
        f"**Code:** `{_MODULE_PATH}.UserViewSet_post`"
    ),
    responses={
        201: OpenApiResponse(description="si el correo existe, te llegara una notificacion con los pasos siguientes"),
    }
)
class EmailUpdateAPIView(SentryErrorHandlerMixin, UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmailUpdateSerializer
    
    def _post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        message = "si el correo existe, te llegara una notificacion con los pasos siguientes"

        user = request.user

        try:
            usuario_email = User.objects.get(email=email)
            return Response(
                {"message": message}, 
                status=status.HTTP_200_OK
            )
        except User.DoesNotExist:
            confirm_url = UsersRegisterService.get_confirmation_url(user,request, email)
            UpdateUserEmail.send_email(
                to_email=email,
                confirm_url=confirm_url,
                nombre=user.username
            )
            self.logger.info(f'Enviando email de confirmación a {user.username} a su nuevo correo {email}')
            return Response(
                {"message": message},
                status=status.HTTP_200_OK
            )


