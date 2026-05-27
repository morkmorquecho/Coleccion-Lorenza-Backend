from django.contrib import admin
from modeltranslation.admin import TranslationAdmin
from blog.models import Blog
from core.mixins import SoftDeleteAdminMixin

@admin.register(Blog)
class BlogAdmin(SoftDeleteAdminMixin, TranslationAdmin):
    list_display = ('id', 'is_active', 'title', 'status', 'published_at')
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
            "fields": ("status", "published_at", "section")
        }),
        ("Metadata", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )