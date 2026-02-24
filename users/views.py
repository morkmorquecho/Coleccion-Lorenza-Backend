from django.shortcuts import render
from rest_framework.generics import UpdateAPIView, GenericAPIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from core.mixins import SentryErrorHandlerMixin, ViewSetSentryMixin
from core.permission import IsOwner
from core.responses.messages import UserMessages
from users.docs.schemas import ADDRESS_SET_DEFAULT, ADDRESS_VIEWSET, EMAIL_UPDATE
from users.serializers import EmailUpdateSerializer, AddressSerializer
from auth.services import UsersRegisterService
from core.services.email_service import ConfirmUserEmail,UpdateUserEmail
from django.contrib.auth import get_user_model
from rest_framework.response import Response
from rest_framework import viewsets, status, permissions
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, extend_schema_view, OpenApiParameter, OpenApiResponse
from rest_framework.decorators import action
from .models import Address
_MODULE_PATH = __name__

User = get_user_model()

@EMAIL_UPDATE
class EmailUpdateAPIView(SentryErrorHandlerMixin, GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = EmailUpdateSerializer
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        email = serializer.validated_data['email']
        user = request.user
       
        
        # Si el email ya está registrado, solo avisar (no enviar email)
        if User.objects.filter(email=email).exists():
            return Response(
                {"message": UserMessages.EMAIL_SENT_IF_EXISTS}, 
                status=status.HTTP_200_OK
            )
        
        # Si es un email nuevo, enviar confirmación
        confirm_url = UsersRegisterService.get_confirmation_url(user, request, email)
        UpdateUserEmail.send_email(
            to_email=email,
            confirm_url=confirm_url,
            nombre=user.username
        )
        self.logger.info(f'Enviando email de confirmación a {user.username} a su nuevo correo {email}')
        
        return Response(
            {"message": UserMessages.EMAIL_SENT_IF_EXISTS},
            status=status.HTTP_200_OK
        )

@ADDRESS_VIEWSET
class AddressViewSet(ViewSetSentryMixin, viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwner]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False): 
                return Address.objects.none()
        return Address.objects.filter(user=self.request.user).order_by('-is_default', '-created_at')

    @ADDRESS_SET_DEFAULT
    @action(detail=True, methods=['patch'], url_path='set-default')
    def set_default(self, request, pk=None):
        """Endpoint conveniente para marcar una dirección como predeterminada."""
        address = self.get_object()  # Aplica has_object_permission internamente
        Address.objects.filter(user=request.user, is_default=True).update(is_default=False)
        address.is_default = True
        address.save(update_fields=['is_default'])
        return Response(self.get_serializer(address).data)