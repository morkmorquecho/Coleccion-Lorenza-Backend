from datetime import date
from decimal import Decimal
from rest_framework import serializers
from core.mixins import CurrencyMixin
from pieces.models import Piece
from users.models import Address
from users.serializers import AddressSerializer
from .models import CouponUsage, Order, OrderItem, Payment, ShippingTracking, Coupon

class OrderItemInputSerializer(serializers.Serializer):
    piece = serializers.PrimaryKeyRelatedField(queryset=Piece.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class CheckoutSerializer(serializers.Serializer):
    address = serializers.PrimaryKeyRelatedField(queryset=Address.objects.all())
    payment_method = serializers.ChoiceField(choices=['card', 'paypal'])
    items = OrderItemInputSerializer(many=True)
    coupon_code = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate_address(self, address):
        user = self.context['request'].user
        if address.user != user:
            raise serializers.ValidationError("Esta dirección no te pertenece.")
        return address

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("Debes enviar al menos un item.")
        return items

    def validate_coupon_code(self, code):
        if not code:
            return None
        today = date.today()
        try:
            coupon = Coupon.objects.get(
                code=code,
                valid_from__lte=today,
                valid_until__gte=today
            )
        except Coupon.DoesNotExist:
            raise serializers.ValidationError("Cupón inválido o expirado.")

        if not coupon.has_uses_remaining():
            raise serializers.ValidationError("Este cupón ha alcanzado su límite de usos.")

        user = self.context['request'].user
        if CouponUsage.objects.filter(user=user, coupon=coupon).exists():
            raise serializers.ValidationError("Ya usaste este cupón anteriormente.")

        return coupon


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = '__all__'


class CouponUsageSerializer(serializers.ModelSerializer):
    class Meta:
        model = CouponUsage
        fields = '__all__'


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        exclude = ['external_id']


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    coupon_usage = CouponUsageSerializer(many=True, read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = '__all__'


class PieceSnapshotSerializer(serializers.ModelSerializer):
    """Solo los campos de pieza que necesita el modal"""
    class Meta:
        model = Piece
        fields = ['id', 'title', 'thumbnail_path']


class OrderItemDetailSerializer(serializers.ModelSerializer):
    piece = PieceSnapshotSerializer(read_only=True)
    price_snapshot = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['id', 'quantity', 'price_snapshot', 'piece']

    def get_price_snapshot(self, obj):
        return self.context['serializer']._to_currencies(obj.price_snapshot)


class OrderDetailSerializer(CurrencyMixin, serializers.ModelSerializer):
    items = OrderItemDetailSerializer(many=True, read_only=True)
    can_be_cancelled = serializers.SerializerMethodField()
    address = AddressSerializer(read_only=True)
    total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'total', 'status', 'address', 'items', 'can_be_cancelled']

    def get_total(self, obj):
        return self.context['serializer']._to_currencies(obj.total)

    def get_can_be_cancelled(self, obj):
        return obj.can_be_cancelled()


class ShippingTrackingSerializer(CurrencyMixin, serializers.ModelSerializer):
    """Ligero — para el listado"""
    total = serializers.SerializerMethodField()
    tracking_url = serializers.SerializerMethodField()

    class Meta:
        model = ShippingTracking
        fields = '__all__'

    def get_tracking_url(self, obj):
        return obj.get_tracking_url()

    def get_total(self, obj):
        return self._to_currencies(obj.order.total)


class ShippingTrackingDetailSerializer(CurrencyMixin, serializers.ModelSerializer):
    """Completo — para el modal"""
    order = serializers.SerializerMethodField()
    tracking_url = serializers.SerializerMethodField()

    class Meta:
        model = ShippingTracking
        fields = '__all__'

    def get_tracking_url(self, obj):
        return obj.get_tracking_url()

    def get_order(self, obj):
        return OrderDetailSerializer(
            obj.order,
            context={**self.context, 'serializer': self}
        ).data

class UpdateTrackingNumberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingTracking
        fields = ['tracking_number']

    def validate_tracking_number(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError('El número de rastreo no puede estar vacío.')
        return value.strip()