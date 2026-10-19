from django.urls import path, include #type:ignore
from rest_framework.routers import DefaultRouter #type:ignore

from .views.usuario_views import *
from .views.login_views import *
<<<<<<< pruebas2
from .views.publicacion_views import *
from .views.comunidad_views import *


router = DefaultRouter()
router.register(r'usuarios', RegistroUsuarioViewSet, basename='usuario')
router.register(r'publicaciones', PublicacionViewSet, basename ='publicacion')
router.register(r'comentarios', ComentarioViewSet, basename='comentario')
router.register(r'comunidades', ComunidadViewSet, basename='comunidad')
router.register(r'mensajes-comunidad', MensajeComunidadViewSet, basename='mensaje-comunidad')

=======
from .views.media_views import *
from .views.calificacion_views import CalificacionViewSet

router = DefaultRouter()
router.register(r'usuarios', RegistroUsuarioViewSet, basename='usuario')
router.register(r'calificaciones', CalificacionViewSet, basename='calificacion')
#router.register(r'publicacion',)
>>>>>>> sebas

urlpatterns = [
    path('api/', include(router.urls)),
    path('api/login/', LoginAPIView.as_view(), name='api_login'), 
   
]