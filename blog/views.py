from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet

from blog.doc.schema import BLOG_VIEWSET
from blog.models import Blog
from blog.serializer import BlogSerializer
from core.mixins import ViewSetSentryMixin
from core.permission import IsAdminOrReadOnly
from pieces.models import Piece

# Create your views here.
@BLOG_VIEWSET
class BlogViewSet(ViewSetSentryMixin, ModelViewSet):
    queryset = Blog.objects.all()
    serializer_class = BlogSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'
