from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views.usuario_views import *
from .views.login_views import *

router = DefaultRouter()
router.register(r'usuarios', RegistroUsuarioViewSet, basename='usuario')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/login/', LoginAPIView.as_view(), name='api_login'), 
]