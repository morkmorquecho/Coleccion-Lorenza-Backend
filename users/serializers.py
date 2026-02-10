from dj_rest_auth.registration.serializers import RegisterSerializer
from allauth.account import app_settings as allauth_settings
from django.contrib.auth.hashers import check_password

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