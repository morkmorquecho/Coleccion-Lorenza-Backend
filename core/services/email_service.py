import resend
import threading
import logging
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from decouple import config

resend.api_key = config('RESEND_API_KEY')
logger = logging.getLogger(__name__)

class EmailService:
    @classmethod
    def send_template_email(cls, subject, to_email, template_name, **context):
        try:
            html_content = render_to_string(template_name, context)
            plain_message = strip_tags(html_content)

            thread = threading.Thread(
                target=cls._send,
                args=(subject, plain_message, to_email, html_content)
            )
            thread.daemon = True
            thread.start()
            return True

        except Exception as e:
            logger.exception(f"Error al enviar correo a {to_email}: {e}")
            return False

    @classmethod
    def _send(cls, subject, plain_message, to_email, html_content):
        try:
            params = {
                "from": settings.DEFAULT_FROM_EMAIL,
                "to": [to_email],
                "subject": subject,
                "html": html_content,
                "text": plain_message,
            }
            email = resend.Emails.send(params)
            logger.info(f"Correo enviado a {to_email}, id: {email['id']}")
        except Exception as e:
            logger.exception(f"Error al enviar correo a {to_email}: {e}")


# Todas tus clases quedan igual, no tocar nada abajo
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