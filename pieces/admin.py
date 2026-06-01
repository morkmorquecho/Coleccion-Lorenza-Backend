from django.contrib import admin

from django.contrib import admin

from core.mixins import SoftDeleteAdminMixin
from .models import Discount, PieceDiscount, PiecePhoto, Review, ShippingRate, TypePiece, Section, Piece


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
        'price_base',
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
    fields = ("is_active","image_path", "position","created_at")


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
    list_display = ("is_active", "piece", "image_path", "position","created_at")
    list_select_related = ("piece",)
    search_fields = ("piece__title",)

@admin.register(ShippingRate)
class ShippingRateAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ("region", "kg", "cost")
    search_fields = ("kg",)

@admin.register(Review)
class ReviewAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ['id', 'is_active', 'review_type', 'author_display', 'piece', 'rating', 'created_at']
    list_filter = ['review_type', 'rating', 'piece']
    search_fields = ['user__username', 'external_author', 'piece__title', 'comment']
    readonly_fields = ['created_at', 'updated_at']

    def get_fieldsets(self, request, obj=None):
        # Al editar, adapta los campos según el tipo ya guardado
        review_type = getattr(obj, 'review_type', None) or request.GET.get('review_type', 'internal')

        common_fields = ('piece', 'rating', 'comment', 'photo', 'created_at', 'updated_at')

        if review_type == Review.ReviewType.EXTERNAL:
            return [
                ('Tipo de reseña', {'fields': ('review_type',)}),
                ('Autor externo', {'fields': ('external_author', 'link_etsy')}),
                ('Contenido', {'fields': common_fields}),
            ]
        else:
            return [
                ('Tipo de reseña', {'fields': ('review_type',)}),
                ('Usuario', {'fields': ('user',)}),
                ('Contenido', {'fields': common_fields}),
            ]

    def get_readonly_fields(self, request, obj=None):
        readonly = ['created_at', 'updated_at']

        # Una vez creada, no permitir cambiar el tipo ni el autor
        if obj and obj.pk:
            readonly += ['review_type']
            if obj.review_type == Review.ReviewType.INTERNAL:
                readonly += ['user']       # el usuario no se cambia
            else:
                readonly += ['external_author']  # el autor externo no se cambia

        return readonly

    def save_model(self, request, obj, form, change):
        # Reseña interna sin usuario asignado → asignar al admin que la crea
        if obj.review_type == Review.ReviewType.INTERNAL and not obj.user_id:
            obj.user = request.user

        super().save_model(request, obj, form, change)