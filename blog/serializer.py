from rest_framework import serializers
from blog.models import Blog
from core.mixins import TranslatedFieldsMixin
from pieces.models import Piece, Section

class BlogSerializer(TranslatedFieldsMixin, serializers.ModelSerializer):
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
    title = serializers.SerializerMethodField()
    slug = serializers.SerializerMethodField()
    content = serializers.SerializerMethodField()

    def get_title(self, obj):
        return self.get_translated(obj, 'title')

    def get_slug(self, obj):
        return self.get_translated(obj, 'slug')

    def get_content(self, obj):
        return self.get_translated(obj, 'content')

    class Meta:
        model = Blog
        fields = '__all__'
        read_only_fields = ['is_active']

    def _get_lang(self):
        request = self.context.get('request')
        raw = request.headers.get('Accept-Language', 'es') if request else 'es'
        return raw if raw in {'es', 'en'} else 'es'

    def get_title(self, obj):
        return getattr(obj, f'title_{self._get_lang()}', obj.title_es)

    def get_slug(self, obj):
        return getattr(obj, f'slug_{self._get_lang()}', obj.slug_es)

    def get_content(self, obj):
        return getattr(obj, f'content_{self._get_lang()}', obj.content_es)