import jwt
import datetime
from django.conf import settings

def generar_token_jwt(usuario):
    """Genera un JSON Web Token idéntico al estándar de Node.js"""
    payload = {
        'user_id': usuario.id,
        'nombre_usuario': usuario.nombre_usuario,
        'tipo_usuario': usuario.tipo_usuario,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1), 
        'iat': datetime.datetime.utcnow()
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')