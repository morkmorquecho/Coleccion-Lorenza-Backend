from django.shortcuts import render
from rest_framework.viewsets import ModelViewSet
from django_filters.rest_framework import DjangoFilterBackend
from blog.doc.schema import BLOG_VIEWSET
from blog.filter import BlogFilter
from blog.models import Blog
from blog.serializer import BlogSerializer
from core.mixins import ViewSetSentryMixin
from core.permission import IsAdminOrReadOnly
from pieces.models import Piece

@BLOG_VIEWSET
class BlogViewSet(ViewSetSentryMixin, ModelViewSet):
    queryset = Blog.objects.all()
    serializer_class = BlogSerializer
    permission_classes = [IsAdminOrReadOnly]
    lookup_field = 'slug'
    filter_backends = [DjangoFilterBackend]
    filterset_class = BlogFilter