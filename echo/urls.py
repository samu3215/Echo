from django.urls import path, include #type:ignore
from rest_framework.routers import DefaultRouter #type:ignore

from .views.usuario_views import *
from .views.login_views import *
from .views.media_views import *
from .views.calificacion_views import CalificacionViewSet

router = DefaultRouter()
router.register(r'usuarios', RegistroUsuarioViewSet, basename='usuario')
router.register(r'calificaciones', CalificacionViewSet, basename='calificacion')
#router.register(r'publicacion',)

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/login/', LoginAPIView.as_view(), name='api_login'), 
    path('api/upload/', UploadMediaAPIView.as_view(), name='api_upload_media'),
]