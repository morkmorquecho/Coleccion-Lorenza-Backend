from django.urls import path
from .views import CancelOrderView, CheckoutView, StripeWebhookView

orders_patterns = [
    path('orders/checkout/', CheckoutView.as_view(), name='checkout'),
    path('orders/webhook/', StripeWebhookView.as_view(), name='stripe-webhook'),
    path('orders/<int:pk>/cancel/', CancelOrderView.as_view(), name='cancel-order')
]
