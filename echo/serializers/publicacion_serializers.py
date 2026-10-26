from django.utils.html import strip_tags
from rest_framework import serializers

from echo.models import Comentario, Like, Publicacion, Usuario


class UsuarioBasicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = [
            'id',
            'nombre_usuario',
            'foto_perfil',
            'tipo_usuario',
            'nombre',
            'apellido',
            'nombre_negocio',
        ]
        read_only_fields = fields


class Likeserializer(serializers.ModelSerializer):
    usuario = UsuarioBasicoSerializer(read_only=True)

    class Meta:
        model = Like
        fields = ['id', 'usuario', 'fecha']
        read_only_fields = fields


class ComentarioSerializer(serializers.ModelSerializer):
    usuario = UsuarioBasicoSerializer(read_only=True)

    class Meta:
        model = Comentario
        fields = [
            'id',
            'contenido',
            'fecha_creacion',
            'fecha_actualizacion',
            'activo',
            'usuario',
            'publicacion',
        ]
        read_only_fields = [
            'id',
            'fecha_creacion',
            'fecha_actualizacion',
            'activo',
            'usuario',
        ]

    def validate_contenido(self, value):
        contenido = strip_tags(value).strip()
        if not contenido:
            raise serializers.ValidationError('El comentario no puede estar vacío.')
        return contenido


class CrearPublicacionserializer(serializers.ModelSerializer):
    likes_publicacion = Likeserializer(many=True, read_only=True)
    comentarios_publicacion = ComentarioSerializer(many=True, read_only=True)
    usuario = UsuarioBasicoSerializer(read_only=True)

    class Meta:
        model = Publicacion
        fields = [
            'id',
            'contenido',
            'url_media',
            'tipo_media',
            'fecha_creacion',
            'fecha_actualizacion',
            'activo',
            'usuario',
            'likes_publicacion',
            'comentarios_publicacion',
        ]
        read_only_fields = [
            'id',
            'fecha_creacion',
            'fecha_actualizacion',
            'activo',
            'usuario',
            'likes_publicacion',
            'comentarios_publicacion',
        ]

    def validate_contenido(self, value):
        return strip_tags(value).strip()

    def validate(self, data):
        contenido = data.get(
            'contenido',
            self.instance.contenido if self.instance else '',
        )
        url_media = data.get(
            'url_media',
            self.instance.url_media if self.instance else '',
        )

        if not contenido and not url_media:
            raise serializers.ValidationError(
                'La publicación debe tener al menos una descripción o un archivo multimedia.'
            )

        return data
