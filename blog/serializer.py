

from rest_framework import serializers

from blog.models import Blog
from pieces.models import Piece, Section

class BlogSerializer(serializers.ModelSerializer):
    section = serializers.SlugRelatedField(
        slug_field='key',
        queryset=Section.objects.all()
    )
    pieces = serializers.SlugRelatedField(
        slug_field='slug',
        many=True,
        queryset=Piece.objects.all(),
        required=False
    )

    class Meta:
        model = Blog
        fields = '__all__'
        read_only_fields = ['is_active']

        