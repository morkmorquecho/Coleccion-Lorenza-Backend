from django.urls import include, path
from .views import EmailUpdateAPIView, AddressViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'addresses', AddressViewSet, basename='address')

user_path = ([
    path('me/email/request-change', EmailUpdateAPIView.as_view(), name='request_update_email'),
    path('me/', include(router.urls)),

], 'user')