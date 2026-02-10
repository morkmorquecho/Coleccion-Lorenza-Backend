from django.urls import path
from .views import EmailUpdateAPIView

user_path = ([
    path('me/email/request-change', EmailUpdateAPIView.as_view(), name='request_update_email'),
], 'user')