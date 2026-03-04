from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers
from blog.views import BlogViewSet

router = DefaultRouter()
router.register(r'blog', BlogViewSet,basename='blogs')

blog_patterns = ([
    path('', include(router.urls), name='blog' )
], 'blog')