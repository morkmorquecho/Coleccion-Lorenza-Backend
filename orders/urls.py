from django.urls import include, path
from .views import CancelOrderView, CheckoutView, StripeWebhookView,OrderViewSet, ShippingTrackingViewSet
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

router = DefaultRouter()
router.register(r'orders',OrderViewSet, basename='orders')
router.register(r'shipping-trackings', ShippingTrackingViewSet, basename='shipping-tracking')
orders_router = routers.NestedSimpleRouter(router, r'orders', lookup='order')
orders_router.register(r'shipping-trackings', ShippingTrackingViewSet ,basename='order-shiping-tracking')

orders_patterns = [
    path('orders/checkout/', CheckoutView.as_view(), name='checkout'),
    path('orders/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('orders/<int:pk>/cancel/', CancelOrderView.as_view(), name='cancel-order'),
    path('', include(router.urls)),
    path('', include(orders_router.urls)),
]

