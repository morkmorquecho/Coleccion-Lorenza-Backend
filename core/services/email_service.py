from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

class EmailService:
    @classmethod
    def send_template_email(cls, subject, to_email, template_name, **context):
        """
        Envía un correo basado en una plantilla HTML.
        Permite pasar cualquier cantidad de variables al contexto.
        
        Ejemplo de uso:
            send_template_email(
                subject='Restablecer contraseña',
                to_email=user.email,
                template_name='emails/reset_password.html',
                user=user,
                reset_url='http://localhost:8000/auth/reset-password/...'
            )
        """
        try: 
            html_content = render_to_string(template_name, context)
            plain_message = strip_tags(html_content) 
            
            result = send_mail(
                subject,
                plain_message,
                'noreply@tuapp.com',
                [to_email],
                html_message=html_content
            )
            
            return result == 1
            
        except Exception as e:
            logger.exception(f"Error al enviar correo a {to_email}: {e}")
            return False

class PasswordResetEmail:
    @staticmethod
    def send_email(to_email, **context):
        subject = "Restablecimiento de contraseña"
        template_name = 'emails/auth/password_reset.html'
        EmailService.send_template_email(subject, to_email, template_name, **context)
        
class AccountConfirmationEmail:
    @staticmethod
    def send_email(to_email, **context):
        subject = "Confirmacion de cuenta"
        template_name = 'emails/auth/account_confirmation.html'
        EmailService.send_template_email(subject, to_email, template_name, **context)  

class EmailUpdatedEmail:
    @staticmethod
    def send_email(to_email, **context):
        subject = "Confirmacion de cuenta"
        template_name = 'emails/auth/email_updated.html'
        EmailService.send_template_email(subject, to_email, template_name, **context) 
 
class OrderCreatedAdminEmail:
    @staticmethod
    def send_email(to_email, **context):
        subject = "Nuevo Pedido"
        template_name = 'emails/orders/order_created_admin.html'
        EmailService.send_template_email(subject, to_email, template_name, **context) 

class OrderCreatedUserEmail:
    @staticmethod
    def send_email(to_email, **context):
        subject = "Pago Exitoso"
        template_name = 'emails/orders/order_created_user.html'
        EmailService.send_template_email(subject, to_email, template_name, **context) 
class OrderShippedEmail:
    @staticmethod
    def send_email(to_email, **context):
        subject = "Pedido Enviado"
        template_name = 'emails/orders/order_shipped.html'
        EmailService.send_template_email(subject, to_email, template_name, **context) 

class OrderCancelledUserEmail:
    @staticmethod
    def send_email(to_email, **context):
        subject = "Pedido Cancelado con exito"
        template_name = 'emails/orders/order_cancelled_user.html'
        EmailService.send_template_email(subject, to_email, template_name, **context) 

class OrderCancelledAdminEmail:
    @staticmethod
    def send_email(to_email, **context):
        subject = "Pedido Cancelado"
        template_name = 'emails/orders/order_cancelled_admin.html'
        EmailService.send_template_email(subject, to_email, template_name, **context) 