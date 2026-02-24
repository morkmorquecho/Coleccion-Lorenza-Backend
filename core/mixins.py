# mixins.py
import logging
import sentry_sdk
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError, IntegrityError
from smtplib import SMTPException
from requests.exceptions import RequestException, Timeout, ConnectionError
from rest_framework import permissions
from allauth.socialaccount.providers.oauth2.client import OAuth2Error
from django.contrib import admin
from django.utils.html import format_html
from core.responses.messages import ErrorMessages
from django.db import transaction


class SentryErrorHandlerMixin:
    """
    Mixin para manejo estandarizado de errores con Sentry.
    
    Uso:
        class MiVista(SentryErrorHandlerMixin, generics.GenericAPIView):
            sentry_operation_name = "mi_operacion"  # Opcional
            
            def post(self, request):
                return self.handle_with_sentry(
                    operation=self._procesar_datos,
                    request=request,
                    tags={'feature': 'checkout'},
                )
    """
    
    # Configuración por defecto (puede ser sobrescrita)
    sentry_operation_name = None
    capture_validation_errors = False  # No enviar validaciones a Sentry

    #Nos permite usar logger sin tener que definirlo en cada vista, su uso es simple logger.ingo - warning - error
    @property
    def logger(self):
        """Lazy logger initialization - se crea automáticamente con el módulo de la vista"""
        if not hasattr(self, '_logger'):
            self._logger = logging.getLogger(self.__class__.__module__)
        return self._logger

    def handle_with_sentry(
        self,
        operation,
        request,
        tags=None,
        extra=None,
        success_message=None,
        success_status=status.HTTP_200_OK
    ):
        """
        Ejecuta una operación con manejo automático de errores y Sentry.
        
        Args:
            operation: Función a ejecutar
            request: Request object de Django
            tags: Dict de tags adicionales para Sentry
            extra: Dict de datos extra para Sentry
            success_message: Mensaje de respuesta exitosa
            success_status: Status code de respuesta exitosa
        """
        tags = tags or {}
        extra = extra or {}
        
        # Agregar tags por defecto
        default_tags = {
            'view': self.__class__.__name__,
            'method': request.method,
        }
        if self.sentry_operation_name:
            default_tags['operation'] = self.sentry_operation_name
        
        tags = {**default_tags, **tags}
        
        try:
            # Ejecutar operación
            result = operation(request)
            
            # Si la operación retorna Response, devolverla
            if isinstance(result, Response):
                return result
            
            # Si retorna data, crear Response
            return Response(
                result or success_message or {'detail':ErrorMessages.DEFAULT_SUCCESS},
                status=success_status
            )

        except OAuth2Error as e:
            return self._handle_oauth_error(e, request, tags, extra)
        
        # Errores de validación (NO enviar a Sentry por defecto)
        except ValidationError as e:
            return self._handle_validation_error(e, tags, extra)
        
        except DjangoValidationError as e:
            return self._handle_django_validation_error(e, tags, extra)
        
        # Errores de BD esperados (NO enviar a Sentry)
        except IntegrityError as e:
            return self._handle_integrity_error(e, tags, extra)
        
        # Errores de BD críticos (SÍ enviar a Sentry)
        except DatabaseError as e:
            return self._handle_database_error(e, request, tags, extra)
        
        # Errores de email (WARNING en Sentry)
        except SMTPException as e:
            return self._handle_email_error(e, request, tags, extra)
        
        # Errores de APIs externas
        except Timeout as e:
            return self._handle_timeout_error(e, request, tags, extra)
        
        except ConnectionError as e:
            return self._handle_connection_error(e, request, tags, extra)
        
        except RequestException as e:
            return self._handle_request_error(e, request, tags, extra)
        
        # Error inesperado (SÍ enviar a Sentry)
        except Exception as e:
            return self._handle_unexpected_error(e, request, tags, extra)
    
    # Métodos internos de manejo
    def _handle_oauth_error(self, exception, request, tags, extra):
        """Manejo de errores de OAuth (esperados, no críticos)"""
        # Loguear en auth.log
        if hasattr(self, 'log_auth_event'):
            try:
                self.log_auth_event(
                    'google_oauth_error',
                    user=None,
                    success=False,
                    provider=tags.get('provider', 'unknown'),
                    error_type='OAuth2Error',
                    error_message=str(exception),
                    ip=request.META.get('REMOTE_ADDR')
                )
            except Exception:
                pass  # No fallar si el log falla
        
        # Log estándar
        self.logger.warning(
            f"OAuth error en {self.__class__.__name__}: {str(exception)}",
            extra=extra,
            exc_info=True
        )
        
        # Enviar a Sentry como WARNING
        self._capture_to_sentry(
            exception,
            level="warning",
            tags={**tags, 'error_type': 'oauth'},
            extra=extra,
            request=request
        )
        
        return Response(
            {'detail': ErrorMessages.OAUTH_ERROR},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    def _handle_validation_error(self, exception, tags, extra):
        """Manejo de ValidationError de DRF"""
        self.logger.warning(
            f"Error de validación en {self.__class__.__name__}",
            extra={'errors': str(exception.detail), **extra}
        )
        
        if self.capture_validation_errors:
            self._capture_to_sentry(
                exception, 
                level="info",
                tags={**tags, 'error_type': 'validation'},
                extra=extra
            )
        
        # Re-lanzar para que DRF lo maneje
        raise
    
    def _handle_django_validation_error(self, exception, tags, extra):
        """Manejo de ValidationError de Django"""
        self.logger.warning(
            f"Error de validación Django en {self.__class__.__name__}",
            extra={'error': str(exception), **extra}
        )
        
        return Response(
            {'detail': ErrorMessages.INVALID_DATA, 'errors': exception.message_dict if hasattr(exception, 'message_dict') else str(exception)},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    def _handle_integrity_error(self, exception, tags, extra):
        """Manejo de IntegrityError (duplicados, FK)"""
        self.logger.info(
            f"Error de integridad en {self.__class__.__name__}",
            extra={'error': str(exception), **extra}
        )
        
        # Determinar mensaje según el error
        error_msg = str(exception).lower()
        if 'unique' in error_msg or 'duplicate' in error_msg:
            message = ErrorMessages.RESOURCE_EXISTS
            status_code = status.HTTP_409_CONFLICT
        elif 'foreign key' in error_msg:
            message = ErrorMessages.INVALID_REFERENCE
            status_code = status.HTTP_400_BAD_REQUEST
        else:
            message = ErrorMessages.DATA_INTEGRITY_ERROR
            status_code = status.HTTP_400_BAD_REQUEST
        
        return Response(
            {'detail': message},
            status=status_code
        )
    
    def _handle_database_error(self, exception, request, tags, extra):
        """Manejo de DatabaseError crítico"""
        self.logger.error(
            f"Error crítico de BD en {self.__class__.__name__}",
            extra=extra,
            exc_info=True
        )
        
        self._capture_to_sentry(
            exception,
            level="error",
            tags={**tags, 'error_type': 'database'},
            extra=extra,
            request=request
        )
        
        return Response(
            {'detail': ErrorMessages.DATABASE_ERROR},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    def _handle_email_error(self, exception, request, tags, extra):
        """Manejo de error de email (no crítico)"""
        self.logger.warning(
            f"Error enviando email en {self.__class__.__name__}",
            extra=extra,
            exc_info=True
        )
        
        self._capture_to_sentry(
            exception,
            level="warning",
            tags={**tags, 'error_type': 'email'},
            extra=extra,
            request=request
        )
        
        # No fallar la operación por email
        return Response(
            {'detail': ErrorMessages.EMAIL_NOTIFICATION_PENDING},
            status=status.HTTP_200_OK
        )
    
    def _handle_timeout_error(self, exception, request, tags, extra):
        """Manejo de timeout en API externa"""
        self.logger.warning(
            f"Timeout en API externa en {self.__class__.__name__}",
            extra=extra,
            exc_info=True
        )
        
        self._capture_to_sentry(
            exception,
            level="warning",
            tags={**tags, 'error_type': 'timeout'},
            extra=extra,
            request=request
        )
        
        return Response(
            {'detail': ErrorMessages.SERVICE_TIMEOUT},
            status=status.HTTP_504_GATEWAY_TIMEOUT
        )
    
    def _handle_connection_error(self, exception, request, tags, extra):
        """Manejo de error de conexión"""
        self.logger.error(
            f"Error de conexión en {self.__class__.__name__}",
            extra=extra,
            exc_info=True
        )
        
        self._capture_to_sentry(
            exception,
            level="error",
            tags={**tags, 'error_type': 'connection'},
            extra=extra,
            request=request
        )
        
        return Response(
            {'detail': ErrorMessages.SERVICE_UNAVAILABLE},
            status=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    def _handle_request_error(self, exception, request, tags, extra):
        """Manejo de error general de requests"""
        self.logger.error(
            f"Error en request externa en {self.__class__.__name__}",
            extra=extra,
            exc_info=True
        )
        
        self._capture_to_sentry(
            exception,
            level="error",
            tags={**tags, 'error_type': 'external_api'},
            extra=extra,
            request=request
        )
        
        return Response(
            {'detail': ErrorMessages.EXTERNAL_API_ERROR},
            status=status.HTTP_502_BAD_GATEWAY
        )
    
    def _handle_unexpected_error(self, exception, request, tags, extra):
        """Manejo de error inesperado"""
        self.logger.critical(
            f"Error inesperado en {self.__class__.__name__}",
            extra=extra,
            exc_info=True
        )
        
        self._capture_to_sentry(
            exception,
            level="error",
            tags={**tags, 'error_type': 'unexpected'},
            extra=extra,
            request=request
        )
        
        return Response(
            {'detail': ErrorMessages.UNEXPECTED_ERROR},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    
    def _capture_to_sentry(self, exception, level, tags, extra, request=None):
        """Capturar excepción en Sentry con contexto"""
        with sentry_sdk.push_scope() as scope:
            scope.level = level
            
            # Agregar tags
            for key, value in tags.items():
                scope.set_tag(key, str(value))
            
            # Agregar extra
            for key, value in extra.items():
                scope.set_extra(key, value)
            
            # Agregar contexto de request si existe
            if request:
                scope.set_context("request", {
                    "ip": request.META.get('REMOTE_ADDR'),
                    "user_agent": request.META.get('HTTP_USER_AGENT', '')[:200],
                    "path": request.path,
                    "method": request.method
                })
                
                if hasattr(request, 'user') and request.user.is_authenticated:
                    scope.set_user({
                        'id': request.user.id,
                        'email': request.user.email,
                        'username': request.user.username
                    })
            
            sentry_sdk.capture_exception(exception)


class ViewSetSentryMixin(SentryErrorHandlerMixin):
    """
    Mixin que envuelve automáticamente los métodos de ViewSet.
    
    Uso:
        class ProductViewSet(ViewSetSentryMixin, viewsets.ModelViewSet):
            # Automáticamente maneja errores en todos los métodos
            pass
    
    IMPORTANTE: NO sobrescribas create/update/destroy, usa perform_create/perform_update/perform_destroy
    """
    
    def handle_exception(self, exc):
        """
        Sobrescribe el manejador de excepciones de DRF.
        Este método es llamado automáticamente cuando hay una excepción.
        """
        # Dejar que ValidationError de DRF se maneje normalmente
        if isinstance(exc, ValidationError):
            return super().handle_exception(exc)
        
        # Para otros errores, usar nuestro manejador con Sentry
        tags = {
            'view': self.__class__.__name__,
            'method': self.request.method,
            'action': getattr(self, 'action', 'unknown')
        }
        extra = {
            'view_name': self.__class__.__name__,
            'action': getattr(self, 'action', 'unknown')
        }
        
        # Manejar según tipo de error
        if isinstance(exc, IntegrityError):
            return self._handle_integrity_error(exc, tags, extra)
        elif isinstance(exc, DatabaseError):
            return self._handle_database_error(exc, self.request, tags, extra)
        elif isinstance(exc, SMTPException):
            return self._handle_email_error(exc, self.request, tags, extra)
        elif isinstance(exc, Timeout):
            return self._handle_timeout_error(exc, self.request, tags, extra)
        elif isinstance(exc, ConnectionError):
            return self._handle_connection_error(exc, self.request, tags, extra)
        elif isinstance(exc, RequestException):
            return self._handle_request_error(exc, self.request, tags, extra)
        else:
            # Para otros errores, usar el manejador de DRF pero logear a Sentry
            self._capture_to_sentry(
                exc,
                level="error",
                tags={**tags, 'error_type': 'unexpected'},
                extra=extra,
                request=self.request
            )
            return super().handle_exception(exc)
    
class SoftDeleteAdminMixin:
    """
    Mixin para que el admin vea todos los registros
    incluyendo los eliminados con soft delete.
    """
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')

    def get_readonly_fields(self, request, obj=None):
        audit_fields = {'created_at', 'updated_at', 'deleted_at'}
        existing = set(super().get_readonly_fields(request, obj))
        return tuple(existing | audit_fields)

    def get_queryset(self, request):
        return self.model.all_objects.all()

    def estado_registro(self, obj):
        if obj.is_deleted:
            return format_html(
                '<span style="color: red; font-weight: bold;">🗑 Eliminado ({})</span>',
                obj.deleted_at.strftime("%d/%m/%Y %H:%M")
            )
        if not obj.is_active:
            return format_html('<span style="color: orange;">⚠ Inactivo</span>')
        return format_html('<span style="color: green;">✓ Activo</span>')

    estado_registro.short_description = "Estado"

    actions = ['action_restore', 'action_deactivate']

    def action_restore(self, request, queryset):
        queryset.update(deleted_at=None, is_active=True)
        self.message_user(request, f"{queryset.count()} registro(s) restaurados.")
    action_restore.short_description = "Restaurar registros seleccionados"

    def action_deactivate(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f"{queryset.count()} registro(s) desactivados.")
    action_deactivate.short_description = "Desactivar registros seleccionados"

class ImagenPKMixin:
    """
    Mixin para modelos que tienen ImageFields y necesitan
    que el archivo se nombre usando el PK del objeto.
    
    Uso:
        class pieces(ImagenPKMixin, models.Model):
            imagen = models.ImageField(...)
        
        # Si tienes varios ImageFields:
        class pieces(ImagenPKMixin, models.Model):
            imagen_principal = models.ImageField(...)
            imagen_secundaria = models.ImageField(...)
    """

    def _get_image_fields(self):
        """Detecta automáticamente todos los ImageFields del modelo."""
        from django.db.models import ImageField
        return [
            f.attname for f in self._meta.get_fields()
            if isinstance(f, ImageField)
        ]

    def save(self, *args, **kwargs):
        if not self.pk:
            imagenes_temporales = {}
            for field_name in self._get_image_fields():
                imagenes_temporales[field_name] = getattr(self, field_name)
                setattr(self, field_name, None)

            with transaction.atomic():
                super().save(*args, **kwargs)
                for field_name, valor in imagenes_temporales.items():
                    setattr(self, field_name, valor)
                kwargs.pop('force_insert', None)
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)