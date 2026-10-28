import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
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


class EsDueno(BasePermission):
    
    def has_object_permission(self, request, view, obj):

        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True      

        if isinstance(obj, Usuario):
            return obj.id == request.user.id

        if hasattr(obj, 'usuario'):
            return obj.usuario.id == request.user.id

        if hasattr(obj, 'usuario_califica'):
            return obj.usuario_califica.id == request.user.id
            
        return False