from rest_framework import serializers

from pieces.models import Piece
from users.models import Address
from .models import Order, OrderItem, Payment, ShippingTracking



class OrderItemInputSerializer(serializers.Serializer):
    piece = serializers.PrimaryKeyRelatedField(queryset=Piece.objects.all())
    quantity = serializers.IntegerField(min_value=1)


class CheckoutSerializer(serializers.Serializer):
    address = serializers.PrimaryKeyRelatedField(queryset=Address.objects.all())
    payment_method = serializers.ChoiceField(choices=['card', 'paypal'])
    items = OrderItemInputSerializer(many=True)

    def validate_address(self, address):
        user = self.context['request'].user
        if address.user != user:
            raise serializers.ValidationError("Esta dirección no te pertenece.")
        return address

    def validate_items(self, items):
        if not items:
            raise serializers.ValidationError("Debes enviar al menos un item.")
        return items