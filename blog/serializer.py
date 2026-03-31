

from rest_framework import serializers

from blog.models import Blog


class BlogSerializer(serializers.ModelSerializer):
    section = serializers.SlugRelatedField(
        slug_field='section',
        read_only=True
    )
    class Meta:
        model = Blog
        fields = '__all__'