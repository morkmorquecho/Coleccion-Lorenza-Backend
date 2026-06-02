
from email.headerregistry import Address
from django.db.models.signals import post_delete
from django.dispatch import receiver

@receiver(post_delete, sender=Address)
def set_default_on_delete(sender, instance, **kwargs):
    remaining = Address.objects.filter(user=instance.user)
    if remaining.count() == 1:
        remaining.update(is_default=True)