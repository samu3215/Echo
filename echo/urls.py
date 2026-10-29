from django.urls import path, include #type:ignore
from rest_framework.routers import DefaultRouter #type:ignore

from .views.usuario_views import *
from .views.login_views import *
from .views.publicacion_views import *
from .views.comunidad_views import *
from .views.recuperacion_views import *
from .views.calificacion_views import *

router = DefaultRouter()
router.register(r'usuarios', RegistroUsuarioViewSet, basename='usuario')
router.register(r'publicaciones', PublicacionViewSet, basename ='publicacion')
router.register(r'comentarios', ComentarioViewSet, basename='comentario')
router.register(r'comunidades', ComunidadViewSet, basename='comunidad')
router.register(r'mensajes-comunidad', MensajeComunidadViewSet, basename='mensaje-comunidad')
router.register(r'calificaciones', CalificacionViewSet, basename='calificacion')

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/login/', LoginAPIView.as_view(), name='api_login'), 
    path('api/recuperacion/solicitar-codigo/',SolicitarCodigoAPIView.as_view(),name='solicitar_codigo_recuperacion',),
    path('api/recuperacion/verificar-codigo/',VerificarCodigoAPIView.as_view(),name='verificar_codigo_recuperacion',),
    path('api/recuperacion/restablecer-contrasena/',RestablecerContrasenaAPIView.as_view(),name='restablecer_contrasena',),
    path('api/registro/enviar-codigo/', EnviarCodigoRegistroAPIView.as_view(), name='enviar_codigo_registro'),
    path('api/registro/verificar-codigo/', VerificarCodigoRegistroAPIView.as_view(), name='verificar_codigo_registro'),
   
]