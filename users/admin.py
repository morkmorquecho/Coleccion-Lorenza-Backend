from django.contrib import admin

# Register your models here.
from django.contrib import admin

from core.mixins import SoftDeleteAdminMixin
from .models import Address


@admin.register(Address)
class AddressAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "id",
        'is_active',
        "user",
        "recipient_name",
        "country",
        "state",
        "city",
        "postal_code",
        "is_default",
        'created_at',
        'updated_at',
        'deleted_at',
    )
    list_filter = ("country", "state", "city", "is_default")
    search_fields = (
        "user__username",
        "recipient_name",
        "city",
        "postal_code",
        "street",
    )
    ordering = ("-is_default", "city")