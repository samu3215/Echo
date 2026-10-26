from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views.login_views import LoginAPIView
from .views.media_views import UploadMediaAPIView
from .views.recuperacion_views import (
    RestablecerContrasenaAPIView,
    SolicitarCodigoAPIView,
    VerificarCodigoAPIView,
)
from .views.usuario_views import RegistroUsuarioViewSet

router = DefaultRouter()
router.register(r'usuarios', RegistroUsuarioViewSet, basename='usuario')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/login/', LoginAPIView.as_view(), name='api_login'),
    path('api/upload/', UploadMediaAPIView.as_view(), name='api_upload_media'),
    path(
        'api/recuperacion/solicitar-codigo/',
        SolicitarCodigoAPIView.as_view(),
        name='solicitar_codigo_recuperacion',
    ),
    path(
        'api/recuperacion/verificar-codigo/',
        VerificarCodigoAPIView.as_view(),
        name='verificar_codigo_recuperacion',
    ),
    path(
        'api/recuperacion/restablecer-contrasena/',
        RestablecerContrasenaAPIView.as_view(),
        name='restablecer_contrasena',
    ),
]