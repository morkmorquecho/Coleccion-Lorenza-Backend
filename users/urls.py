from django.urls import include, path
from .views import EmailUpdateAPIView, AddressViewSet, WishListViewSet
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register(r'addresses', AddressViewSet, basename='address')
router.register(r'wishlist', WishListViewSet, basename='wishlist')

users_patterns = ([
    path('me/', include(router.urls)),
    path('me/email/request-change', EmailUpdateAPIView.as_view(), name='request_update_email'),
], 'user')