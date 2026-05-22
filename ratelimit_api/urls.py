from django.urls import path
from .views import RequestView, StatsView

urlpatterns = [
    path('request', RequestView.as_view()),
    path('stats', StatsView.as_view()),
]