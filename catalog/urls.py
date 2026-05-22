from django.urls import path
from .views import ProductListCreateView, ProductDetailView, ProductMediaView

urlpatterns = [
    path('products', ProductListCreateView.as_view()),
    path('products/<str:product_id>', ProductDetailView.as_view()),
    path('products/<str:product_id>/media', ProductMediaView.as_view()),
]