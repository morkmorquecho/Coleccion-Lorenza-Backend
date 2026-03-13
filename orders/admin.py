from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.utils.html import format_html

from core.mixins import SoftDeleteAdminMixin
from .models import (
    Coupon,
    Order,
    OrderItem,
    ShippingTracking,
    Payment,
    CouponUsage,
)


# ---------- INLINES ----------

class OrderItemInline(SoftDeleteAdminMixin, admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ("price_snapshot",)


class PaymentInline(SoftDeleteAdminMixin, admin.TabularInline):
    model = Payment
    extra = 0
    readonly_fields = ("external_id", "amount", "payment_method", "status")


class ShippingTrackingInline(SoftDeleteAdminMixin, admin.TabularInline):
    model = ShippingTracking
    extra = 0
    readonly_fields = ("tracking_link",)

    def tracking_link(self, obj):
        if obj.get_tracking_url():
            return format_html(
                '<a href="{}" target="_blank">Ver rastreo</a>',
                obj.get_tracking_url(),
            )
        return "-"
    tracking_link.short_description = "Tracking"


# ---------- ADMINS ----------

@admin.register(Coupon)
class CouponAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "code",
        "percentage",
        "valid_from",
        "valid_until",
        "created_at",
    )
    search_fields = ("code",)
    list_filter = ("valid_from", "valid_until")
    ordering = ("-created_at",)


@admin.register(Order)
class OrderAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "total",
        "status",
        "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("id", "user__username", "user__email")
    inlines = [OrderItemInline, PaymentInline, ShippingTrackingInline]
    ordering = ("-created_at",)
    readonly_fields = ("total",)


@admin.register(OrderItem)
class OrderItemAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "id",
        "order",
        "piece",
        "quantity",
        "price_snapshot",
        "created_at",
    )
    search_fields = ("order__id", "piece__name")
    list_filter = ("created_at",)


@admin.register(ShippingTracking)
class ShippingTrackingAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "order",
        "carrier",
        "tracking_number",
        "status",
        "shipped_at",
        "delivered_at",
        "tracking_link",
    )
    list_filter = ("carrier", "status")
    search_fields = ("tracking_number", "order__id")
    readonly_fields = ("tracking_link",)

    def tracking_link(self, obj):
        if obj.get_tracking_url():
            return format_html(
                '<a href="{}" target="_blank">Abrir</a>',
                obj.get_tracking_url(),
            )
        return "-"
    tracking_link.short_description = "Tracking"


@admin.register(Payment)
class PaymentAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "order",
        "amount",
        "payment_method",
        "status",
        "external_id",
        "created_at",
    )
    list_filter = ("status", "payment_method")
    search_fields = ("external_id", "order__id")


@admin.register(CouponUsage)
class CouponUsageAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        "order",
        "coupon",
        "user",
        "discount_applied",
        "created_at",
    )
    list_filter = ("coupon", "created_at")
    search_fields = ("order__id", "coupon__code", "user__username")