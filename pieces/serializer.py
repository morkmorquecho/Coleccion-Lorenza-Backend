from django.utils import timezone
from decimal import Decimal
from pieces.models import Piece, PieceDiscount, PiecePhoto, Section, TypePiece
from rest_framework import serializers

class TypePieceSerializer(serializers.ModelSerializer):
    class Meta:
        model = TypePiece
        fields = "__all__"

class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = "__all__"

class PieceSerializer(serializers.ModelSerializer):
    type = serializers.SlugRelatedField(slug_field='key', read_only=True)
    section = serializers.SlugRelatedField(slug_field='key', read_only=True)

    type_id = serializers.PrimaryKeyRelatedField(
        queryset=TypePiece.objects.all(), source='type', write_only=True
    )
    section_id = serializers.PrimaryKeyRelatedField(
        queryset=Section.objects.all(), source='section', write_only=True
    )

    # Campos calculados
    has_discount = serializers.SerializerMethodField()
    discount_percentage = serializers.SerializerMethodField()
    final_price_mx = serializers.SerializerMethodField()
    final_price_usa = serializers.SerializerMethodField()

    class Meta:
        model = Piece
        fields = [
            "id",
            "title",
            "slug",
            "description",
            "thumbnail_path",
            "quantity",
            "price_mx",
            "price_usa",
            "width",
            "height",
            "length",
            "weight",
            "customizable",
            "featured",
            "type",       
            "type_id",    
            "section",    
            "section_id", 
            
            # calculados
            "has_discount",
            "discount_percentage",
            "final_price_mx",
            "final_price_usa",
        ]

    def _get_active_discount(self, obj):
        """Busca el descuento activo y lo cachea en el contexto del objeto."""
        if not hasattr(obj, "_active_discount"):
            today = timezone.now().date()
            piece_discount = (
                obj.discounts.filter(
                    deleted_at__isnull=True,
                    discount__start_date__lte=today,
                    discount__end_date__gte=today,
                )
                .select_related("discount")
                .first()
            )
            obj._active_discount = piece_discount.discount if piece_discount else None
        return obj._active_discount

    def get_has_discount(self, obj) -> bool:
        return self._get_active_discount(obj) is not None

    def get_discount_percentage(self, obj) -> float | None:
        discount = self._get_active_discount(obj)
        return discount.percentage if discount else None

    def _apply_discount(self, price, discount):
        if not discount:
            return price
        factor = 1 - (Decimal(discount.percentage) / Decimal("100"))
        return round(price * factor, 2)

    def get_final_price_mx(self, obj) -> float:
        return self._apply_discount(obj.price_mx, self._get_active_discount(obj))

    def get_final_price_usa(self, obj) -> float:
        return self._apply_discount(obj.price_usa, self._get_active_discount(obj))
    
class PiecePhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PiecePhoto
        fields = ['id', 'image_path', 'position']

    def validate(self, attrs):
        piece = attrs.get('piece')
        if PiecePhoto.objects.filter(piece=piece).count() >= 10:
            raise serializers.ValidationError("Esta pieza ya tiene el máximo de 10 fotos.")
        return attrs
    

# Serializer dedicado solo para recibir el bulk de subida
class PiecePhotoBulkCreateSerializer(serializers.Serializer):
    # "many files" se maneja con ListField
    images = serializers.ListField(
        child=serializers.ImageField(),
        min_length=1,
        max_length=10
    )

    def validate_images(self, images):
        piece = self.context.get('piece')
        current_count = PiecePhoto.objects.filter(piece=piece).count()
        if current_count + len(images) > 10:
            raise serializers.ValidationError(
                f"Solo puedes subir {10 - current_count} imágenes más."
            )
        return images


# Serializer dedicado solo para el reordenamiento
class PiecePhotoReorderSerializer(serializers.Serializer):
    # Espera una lista de objetos: [{"id": "abc", "position": 1}, ...]
    class ReorderItemSerializer(serializers.Serializer):
        id = serializers.IntegerField()
        position = serializers.IntegerField(min_value=1, max_value=10)

    photos = ReorderItemSerializer(many=True, min_length=1)

    def validate_photos(self, photos):
        # Las posiciones no se pueden repetir en el mismo request
        positions = [p['position'] for p in photos]
        if len(positions) != len(set(positions)):
            raise serializers.ValidationError("No puedes asignar la misma posición a dos fotos.")
        return photos


# Serializer para borrado masivo
class PiecePhotoBulkDeleteSerializer(serializers.Serializer):
    ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1
    )


class PieceDiscountSerializer(serializers.ModelSerializer):
    percentage = serializers.DecimalField(
        source='discount.percentage',
        max_digits=5,
        decimal_places=2,
        read_only=True
    )

    class Meta:
        model = PieceDiscount
        fields = ['id','piece' ,'percentage']    