from django.urls import path, include

urlpatterns = [
    path('', include('ratelimit_api.urls')),
    path('', include('catalog.urls')),
]