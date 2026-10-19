from django.urls import path, include #type:ignore
from rest_framework.routers import DefaultRouter #type:ignore

from .views.usuario_views import *
from .views.login_views import *
from .views.publicacion_views import *
from .views.comunidad_views import *


router = DefaultRouter()
router.register(r'usuarios', RegistroUsuarioViewSet, basename='usuario')
router.register(r'publicaciones', PublicacionViewSet, basename ='publicacion')
router.register(r'comentarios', ComentarioViewSet, basename='comentario')
router.register(r'comunidades', ComunidadViewSet, basename='comunidad')
router.register(r'mensajes-comunidad', MensajeComunidadViewSet, basename='mensaje-comunidad')


urlpatterns = [
    path('api/', include(router.urls)),
    path('api/login/', LoginAPIView.as_view(), name='api_login'), 
   
]