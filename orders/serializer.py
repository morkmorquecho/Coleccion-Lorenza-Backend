from datetime import date
from rest_framework import serializers
from pieces.models import Piece
from users.models import Address
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

        # Verificar que el usuario no lo haya usado antes
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
        fields = '__all__'
        exclude = ['external_id'] 
class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True, source='items')
    coupons = CouponUsageSerializer(many=True, read_only=True, source='coupon_usage')
    payments = PaymentSerializer(many=True, read_only=True, source='payments')

    class Meta:
        model = Order
        fields = '__all__'

class ShippingTrackingSerializer(serializers.ModelSerializer):
    class Meta:
        model = ShippingTracking
        fields = '__all__'