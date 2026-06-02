from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.utils.html import format_html

from core.mixins import SoftDeleteAdminMixin

from .models import Carousel, Collection, ImageCollection

class ImageCollectionInline(SoftDeleteAdminMixin, admin.TabularInline):
    model = ImageCollection
    extra = 1
    fields = ('name', 'year', 'image_preview', 'image_path')
    readonly_fields = ('image_preview',)

    def image_preview(self, obj):
        if obj.image_path:
            return format_html(
                '<img src="{}" style="height: 80px; border-radius: 5px;" />',
                obj.image_path.url
            )
        return "-"
    image_preview.short_description = "Preview"


@admin.register(Collection)
class CollectionAdmin(SoftDeleteAdminMixin, admin.ModelAdmin):
    list_display = ('name', 'thumbnail_preview')
    search_fields = ('name',)
    inlines = [ImageCollectionInline]

    def thumbnail_preview(self, obj):
        if obj.thumbnail_path:
            return format_html(
                '<img src="{}" style="height: 60px; border-radius: 5px;" />',
                obj.thumbnail_path.url
            )
        return "-"
    thumbnail_preview.short_description = "Thumbnail"


@admin.register(Carousel)
class CarouselAdmin(SoftDeleteAdminMixin,admin.ModelAdmin):
    list_display = ('id', 'carousel', 'position', 'image_preview')
    list_filter = ('carousel',)
    ordering = ('carousel', 'position')

    def image_preview(self, obj):
        if obj.img:
            return format_html(
                '<img src="{}" style="height: 60px; border-radius: 5px;" />',
                obj.img.url
            )
        return "-"
    image_preview.short_description = "Preview"


@admin.register(ImageCollection)
class ImageCollectionAdmin(SoftDeleteAdminMixin,admin.ModelAdmin):
    list_display = ('name', 'collection', 'year', 'image_preview')
    list_filter = ('collection', 'year')
    search_fields = ('name',)

    def image_preview(self, obj):
        if obj.image_path:
            return format_html(
                '<img src="{}" style="height: 60px; border-radius: 5px;" />',
                obj.image_path.url
            )
        return "-"
    image_preview.short_description = "Preview"