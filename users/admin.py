from pyexpat.errors import messages

from django.contrib import admin
from core.mixins import SoftDeleteAdminMixin
from .models import Address, WishList
from django.contrib.auth.admin import UserAdmin

from django.contrib.auth import get_user_model
User = get_user_model()


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
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


@admin.action(description="Desactivar usuarios seleccionados")
def deactivate_users(modeladmin, request, queryset):
    updated = queryset.filter(is_active=True).update(is_active=False)
    modeladmin.message_user(
        request,
        f"{updated} usuario(s) desactivado(s).",
        level=messages.SUCCESS,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    actions = [deactivate_users]
    list_display = (
        "id",
        "username",
        "email",
        "is_active",
        "last_login",
        "date_joined",
    )

@admin.register(WishList)
class WishListAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'user',
        'piece',
        'is_active',
        'created_at',
        'updated_at',
    )

    list_filter = (
        'is_active',
        'created_at',
        'updated_at',
    )

    search_fields = (
        'user__username',
        'user__email',
        'piece__title',
    )

    readonly_fields = (
        'created_at',
        'updated_at',
    )

    ordering = ('-created_at',)

    autocomplete_fields = (
        'user',
        'piece',
    )