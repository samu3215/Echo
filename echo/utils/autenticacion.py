import jwt # type: ignore
from django.conf import settings # type: ignore
from rest_framework.authentication import BaseAuthentication # type: ignore
from rest_framework.exceptions import AuthenticationFailed # type: ignore
from rest_framework.permissions import BasePermission # type: ignore
from echo.models import *

class AutenticacionJWT(BaseAuthentication):

    def authenticate(self, request):
        cabecera_autenticacion = request.headers.get('Authorization')

        if not cabecera_autenticacion or not cabecera_autenticacion.startswith('Bearer '):
            return None 

        token = cabecera_autenticacion.split(' ')[1]
        
        try:
            datos_token = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])

            usuario = Usuario.objects.get(id=datos_token['user_id'], activo=True)
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed('El token expiró. Inicia sesión de nuevo.')
        except (jwt.InvalidTokenError, Usuario.DoesNotExist):
            raise AuthenticationFailed('Token inválido o usuario no existe.')

        return (usuario, token)


class RequiereToken(BasePermission):

    def has_permission(self, request, view):
        return bool(request.user and hasattr(request.user, 'tipo_usuario'))

class EsDuenoDelPerfil(BasePermission):
    """
    Permite a cualquiera ver el perfil (lectura), 
    pero SOLO el dueño (el del Token) puede editarlo o borrarlo.
    """
    def has_object_permission(self, request, view, obj):
       
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return obj.id == request.user.id