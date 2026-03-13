from dj_rest_auth.registration.serializers import RegisterSerializer
from allauth.account import app_settings as allauth_settings
from django.contrib.auth.hashers import check_password
from .models import Address
from rest_framework import serializers

class CustomRegisterSerializer(RegisterSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Configurar username según SIGNUP_FIELDS
        username_config = allauth_settings.SIGNUP_FIELDS.get('username', {})
        self.fields['username'].required = username_config.get('required', False)
        
        # Configurar email según SIGNUP_FIELDS
        email_config = allauth_settings.SIGNUP_FIELDS.get('email', {})
        self.fields['email'].required = email_config.get('required', True)

class EmailUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    
    def validate(self, data):
        """Valida que la contraseña sea correcta"""
        user = self.context['request'].user
        
        if not check_password(data['password'], user.password):
            raise serializers.ValidationError({
                'password': 'Contraseña incorrecta.'
            })
        
        return data
    
class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = [
            'id', 'recipient_name', 'country', 'state', 'city',
            'postal_code', 'neighborhood', 'street', 'street_number',
            'phone_number', 'reference', 'apartment_number', 'is_default',
            'created_at', 'updated_at',
        ]

    def validate(self, attrs):
        request = self.context['request']
        user = request.user

        is_default = attrs.get('is_default', False)

        if is_default:
            qs = Address.objects.filter(user=user, is_default=True)

            if self.instance:
                qs = qs.exclude(pk=self.instance.pk)

            if qs.exists():
                raise serializers.ValidationError({
                    "is_default": "El usuario ya tiene una dirección predeterminada."
                })

        return attrs

    def create(self, validated_data):
        user = self.context['request'].user
        if validated_data.get('is_default'):
            Address.objects.filter(user=user, is_default=True).update(is_default=False)
        return Address.objects.create(user=user, **validated_data)

    def update(self, instance, validated_data):
        user = self.context['request'].user
        if validated_data.get('is_default'):
            Address.objects.filter(user=user, is_default=True).exclude(pk=instance.pk).update(is_default=False)
        return super().update(instance, validated_data)