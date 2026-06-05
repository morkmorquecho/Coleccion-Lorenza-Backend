from django.urls import include, path
from .views import CacheDebugView, IPDebugView,CancelOrderView, CheckoutView, ExchangeRateView, IPDebugView, StripeWebhookView,OrderViewSet, ShippingTrackingViewSet, ValidateCouponView
from rest_framework.routers import DefaultRouter
from rest_framework_nested import routers

router = DefaultRouter()
router.register(r'orders',OrderViewSet, basename='orders')
router.register(r'shipping-trackings', ShippingTrackingViewSet, basename='shipping-tracking')

orders_patterns = [
    # path('debug/cache/', CacheDebugView.as_view(), name='debug cache'),
    path('debug/ip/', IPDebugView.as_view(), name='ip-debug'),
    path('orders/checkout/', CheckoutView.as_view(), name='checkout'),
    path('orders/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('orders/<int:pk>/cancel/', CancelOrderView.as_view(), name='cancel-order'),
    path('orders/coupons/validate/', ValidateCouponView.as_view(), name='coupon-validate'),
    path('usd-mxn-rate/', ExchangeRateView.as_view(), name='exchangue'),
    path('', include(router.urls)),
]

