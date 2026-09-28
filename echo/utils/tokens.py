import jwt #type:ignore
import datetime
from django.conf import settings #type:ignore


def generar_token_jwt(usuario):

    ahora = datetime.datetime.now(datetime.timezone.utc)

    payload = {
        'user_id': usuario.id,
        'nombre_usuario': usuario.nombre_usuario,
        'tipo_usuario': usuario.tipo_usuario,
        'exp': ahora + datetime.timedelta(days=1), 
        'iat': ahora
    }

    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')