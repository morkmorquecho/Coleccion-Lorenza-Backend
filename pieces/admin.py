from django.contrib import admin

from django.contrib import admin

from core.mixins import SoftDeleteAdminMixin
from .models import Discount, PieceDiscount, PiecePhoto, TypePiece, Section, Piece


@admin.register(TypePiece)
class TypePieceAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ('id','is_active', 'type', 'key', 'created_at','updated_at')
    search_fields = ('type', 'key')
    ordering = ('type',)


@admin.register(Section)
class SectionAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ('id', 'is_active','section', 'key', 'created_at','updated_at')        
    search_fields = ('section', 'key')
    ordering = ('section',)


@admin.register(Piece)
class PieceAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = (
        'id',
        'is_active',
        'title',
        'price_mx',
        'price_usa',
        'quantity',
        'customizable',
        'featured',
        'type',
        'section',
        'created_at',
        'updated_at',
    )
    list_filter = ('customizable', 'featured', 'type', 'section')
    search_fields = ('title', 'slug', 'description')
    prepopulated_fields = {'slug': ('title',)}
    ordering = ('-created_at',)


class PiecePhotoInline(SoftDeleteAdminMixin, admin.TabularInline):
    model = PiecePhoto
    extra = 1
    readonly_fields = ("created_at",)
    fields = ("is_active","image_path", "created_at")


@admin.register(Discount)
class DiscountAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("is_active","percentage", "start_date", "end_date", "created_at")
    list_filter = ("start_date", "end_date")
    search_fields = ("percentage",)
    ordering = ("-created_at",)


@admin.register(PieceDiscount)
class PieceDiscountAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("is_active", "piece", "discount", "created_at")
    list_select_related = ("piece", "discount")
    search_fields = ("piece__title",)
    autocomplete_fields = ("piece", "discount")
    ordering = ("-created_at",)


@admin.register(PiecePhoto)
class PiecePhotoAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("is_active", "piece", "image_path", "created_at")
    list_select_related = ("piece",)
    search_fields = ("piece__title",)