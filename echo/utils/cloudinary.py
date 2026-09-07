import cloudinary.uploader #type:ignore
from rest_framework.exceptions import ValidationError #type:ignore

FORMATOS_PERMITIDOS = ['image/jpeg', 'image/png', 'image/webp', 'video/mp4']
TAMANO_MAXIMO_MB = 10 

def subir_archivo_cloudinary(archivo, carpeta="general", es_perfil=False):
    """
    Servicio global para subir imágenes o videos a Cloudinary.
    """
    if archivo.size > TAMANO_MAXIMO_MB * 1024 * 1024:
        raise ValidationError(f"El archivo es demasiado grande. El límite es {TAMANO_MAXIMO_MB} MB.")

    if es_perfil and "video" in archivo.content_type:
        raise ValidationError("Las fotos de perfil deben ser imágenes (JPG, PNG, WEBP). No se permiten videos.")

    if archivo.content_type not in FORMATOS_PERMITIDOS:
        raise ValidationError("Formato no soportado. Revisa las extensiones permitidas.")

    try:
        tipo_recurso = "video" if "video" in archivo.content_type else "image"
        
        respuesta = cloudinary.uploader.upload(
            archivo,
            folder=carpeta,
            resource_type=tipo_recurso
        )
        
        return respuesta.get("secure_url")
        
    except Exception as e:
        raise ValidationError(f"Error al subir el archivo al servidor multimedia: {str(e)}")