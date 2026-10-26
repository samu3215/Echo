import cloudinary
import cloudinary.uploader
from cloudinary.exceptions import Error as CloudinaryError
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from rest_framework.exceptions import APIException, ValidationError


FORMATOS_PERMITIDOS = {
    'image/jpeg',
    'image/png',
    'image/webp',
    'video/mp4',
}
TAMANO_MAXIMO_MB = 10


class CloudinaryUploadError(APIException):
    status_code = 502
    default_detail = 'No fue posible subir el archivo al servicio multimedia.'
    default_code = 'cloudinary_upload_failed'


def subir_archivo_cloudinary(archivo, carpeta='general', es_perfil=False):
    if archivo.size > TAMANO_MAXIMO_MB * 1024 * 1024:
        raise ValidationError(
            f'El archivo supera el límite de {TAMANO_MAXIMO_MB} MB.'
        )

    tipo_contenido = getattr(archivo, 'content_type', None)
    if tipo_contenido not in FORMATOS_PERMITIDOS:
        raise ValidationError('Formato no soportado.')
    if es_perfil and tipo_contenido.startswith('video/'):
        raise ValidationError(
            'Las fotos de perfil deben ser imágenes JPG, PNG o WEBP.'
        )

    configuracion = {
        'cloud_name': getattr(settings, 'CLOUDINARY_CLOUD_NAME', None),
        'api_key': getattr(settings, 'CLOUDINARY_API_KEY', None),
        'api_secret': getattr(settings, 'CLOUDINARY_API_SECRET', None),
        'secure': True,
    }
    if not all(configuracion.get(clave) for clave in ('cloud_name', 'api_key', 'api_secret')):
        raise ImproperlyConfigured(
            'Configura CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY y CLOUDINARY_API_SECRET.'
        )

    cloudinary.config(**configuracion)
    tipo_recurso = 'video' if tipo_contenido.startswith('video/') else 'image'
    try:
        respuesta = cloudinary.uploader.upload(
            archivo,
            folder=carpeta,
            resource_type=tipo_recurso,
        )
    except CloudinaryError as error:
        raise CloudinaryUploadError() from error

    url_segura = respuesta.get('secure_url')
    if not url_segura:
        raise CloudinaryUploadError()
    return url_segura
