from django.urls import path

from app.api import views

urlpatterns = [
    path("payments", views.PaymentCreateView.as_view(), name="payment-create"),
]
