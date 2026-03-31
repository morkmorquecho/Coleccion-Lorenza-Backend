from django.contrib import admin

from blog.models import Blog
from core.mixins import SoftDeleteAdminMixin

@admin.register(Blog)
class BlogAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ('id','is_active',"title", "slug", "status", "published_at")
    list_filter = ("status",)
    search_fields = ("title", "slug", "content")
    prepopulated_fields = {"slug": ("title",)}
    readonly_fields = ("created_at", "updated_at")
    filter_horizontal = ("pieces",)
    date_hierarchy = "published_at"

    fieldsets = (
        ("Content", {
            "fields": ("title", "slug", "content", "cover_image")
        }),
        ("Relations", {
            "fields": ("pieces",)
        }),
        ("Publishing", {
            "fields": ("status", "published_at")
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )