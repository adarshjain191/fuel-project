from django.urls import path
from .views import RouteView

urlpatterns = [
    path('api/route/', RouteView.as_view(), name='route_api'),
]
