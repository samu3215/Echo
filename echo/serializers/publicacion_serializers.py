from django.db import transaction
from django.utils.html import strip_tags
from rest_framework import serializers

from echo.models import (
    ArchivoPublicacion,
    Comentario,
    Like,
    Publicacion,
    Usuario,
)


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


class ArchivoPublicacionSerializer(serializers.ModelSerializer):
    url_media = serializers.CharField(required=False)
    tipo_media = serializers.ChoiceField(
        choices=ArchivoPublicacion.TIPO_MEDIA_CHOICES,
        required=False,
    )

    class Meta:
        model = ArchivoPublicacion
        fields = ['id', 'url_media', 'tipo_media', 'orden']
        read_only_fields = ['id']


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
            'comentario_padre',
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

    def validate(self, data):
        publicacion = data.get(
            'publicacion',
            self.instance.publicacion if self.instance else None,
        )
        if publicacion:
            if not publicacion.activo:
                raise serializers.ValidationError(
                    {'publicacion': 'No puedes comentar una publicación inactiva.'}
                )
            if not publicacion.comentarios_activados:
                raise serializers.ValidationError(
                    {'publicacion': 'Los comentarios están desactivados para esta publicación.'}
                )

        comentario_padre = data.get(
            'comentario_padre',
            self.instance.comentario_padre if self.instance else None,
        )
        if (
            comentario_padre
            and publicacion
            and comentario_padre.publicacion_id != publicacion.id
        ):
            raise serializers.ValidationError(
                {'comentario_padre': 'La respuesta debe pertenecer a la misma publicación.'}
            )
        return data


class CrearPublicacionserializer(serializers.ModelSerializer):
    archivos = ArchivoPublicacionSerializer(many=True, required=False)
    likes_publicacion = serializers.SerializerMethodField()
    comentarios_publicacion = serializers.SerializerMethodField()
    usuario = UsuarioBasicoSerializer(read_only=True)

    class Meta:
        model = Publicacion
        fields = [
            'id',
            'descripcion',
            'comentarios_activados',
            'fecha_creacion',
            'fecha_actualizacion',
            'activo',
            'usuario',
            'archivos',
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

    def get_comentarios_publicacion(self, obj):
        comentarios = obj.comentarios_publicacion.filter(
            activo=True,
            usuario__activo=True,
        )
        return ComentarioSerializer(comentarios, many=True, context=self.context).data

    def get_likes_publicacion(self, obj):
        likes = obj.likes_publicacion.filter(usuario__activo=True)
        return Likeserializer(likes, many=True, context=self.context).data

    def validate(self, data):
        for campo, valor in data.items():
            if isinstance(valor, str):
                data[campo] = strip_tags(valor)

        descripcion = data.get(
            'descripcion',
            self.instance.descripcion if self.instance else '',
        )
        if isinstance(descripcion, str):
            descripcion = descripcion.strip()
            data['descripcion'] = descripcion
            if len(descripcion) > 2200:
                raise serializers.ValidationError(
                    {'descripcion': 'La descripción no puede superar los 2200 caracteres.'}
                )

        archivos_enviados = self.initial_data.get('archivos', [])
        if not isinstance(archivos_enviados, list):
            raise serializers.ValidationError(
                {'archivos': 'Debes enviar una lista de archivos multimedia.'}
            )

        if self.instance is None:
            if len(archivos_enviados) > 8:
                raise serializers.ValidationError(
                    {'archivos': 'El límite máximo es de 8 archivos por publicación.'}
                )
            ordenes = set()
            for indice, archivo in enumerate(data.get('archivos', []), start=1):
                if not archivo.get('url_media') or not archivo.get('tipo_media'):
                    raise serializers.ValidationError(
                        {'archivos': 'Cada archivo debe incluir su URL y tipo de medio.'}
                    )
                orden = archivo.get('orden', indice)
                if orden < 1 or orden in ordenes:
                    raise serializers.ValidationError(
                        {'archivos': 'Cada archivo debe tener un orden único mayor que cero.'}
                    )
                archivo['orden'] = orden
                ordenes.add(orden)
            if not descripcion and not archivos_enviados:
                raise serializers.ValidationError(
                    'La publicación debe tener al menos una descripción o un archivo multimedia.'
                )
        else:
            if len(self.instance.archivos.all()) > 8:
                raise serializers.ValidationError(
                    {'archivos': 'Una publicación no puede tener más de 8 archivos.'}
                )

            ids_enviados = []
            for archivo in archivos_enviados:
                archivo_id = archivo.get('id') if isinstance(archivo, dict) else None
                if not archivo_id:
                    raise serializers.ValidationError(
                        {'archivos': 'No está permitido agregar nuevos archivos al editar.'}
                    )
                try:
                    ids_enviados.append(int(archivo_id))
                except (TypeError, ValueError):
                    raise serializers.ValidationError(
                        {'archivos': 'El identificador de archivo no es válido.'}
                    )

            if len(ids_enviados) != len(set(ids_enviados)):
                raise serializers.ValidationError(
                    {'archivos': 'No puedes repetir archivos en la lista.'}
                )

            archivos_actuales = {
                archivo.id: archivo
                for archivo in self.instance.archivos.all()
            }
            if any(archivo_id not in archivos_actuales for archivo_id in ids_enviados):
                raise serializers.ValidationError(
                    {'archivos': 'Solo puedes reordenar archivos de esta publicación.'}
                )
            if len(ids_enviados) > 8:
                raise serializers.ValidationError(
                    {'archivos': 'El límite máximo es de 8 archivos por publicación.'}
                )

            ordenes = []
            for archivo_enviado, archivo_id in zip(archivos_enviados, ids_enviados):
                orden = archivo_enviado.get('orden', archivos_actuales[archivo_id].orden)
                try:
                    orden = int(orden)
                except (TypeError, ValueError):
                    raise serializers.ValidationError(
                        {'archivos': 'El orden de cada archivo debe ser un número entero.'}
                    )
                if orden < 1:
                    raise serializers.ValidationError(
                        {'archivos': 'El orden debe ser mayor que cero.'}
                    )
                ordenes.append((archivo_id, orden))

            ordenes_enviados = [orden for _, orden in ordenes]
            if len(ordenes_enviados) != len(set(ordenes_enviados)):
                raise serializers.ValidationError(
                    {'archivos': 'Cada archivo debe tener un orden único.'}
                )

            descripcion_final = data.get('descripcion', self.instance.descripcion)
            if not descripcion_final and not ids_enviados:
                raise serializers.ValidationError(
                    'No puedes dejar la publicación vacía. Escribe una descripción o conserva los archivos.'
                )

        return data

    def create(self, validated_data):
        archivos_data = validated_data.pop('archivos', [])
        publicacion = Publicacion.objects.create(**validated_data)
        ArchivoPublicacion.objects.bulk_create(
            [
                ArchivoPublicacion(publicacion=publicacion, **archivo)
                for archivo in archivos_data
            ]
        )
        return publicacion

    def update(self, instance, validated_data):
        archivos_data = validated_data.pop('archivos', None)
        with transaction.atomic():
            instance.descripcion = validated_data.get(
                'descripcion',
                instance.descripcion,
            )
            instance.comentarios_activados = validated_data.get(
                'comentarios_activados',
                instance.comentarios_activados,
            )
            instance.save()

            if archivos_data is not None:
                archivos_enviados = self.initial_data.get('archivos', [])
                ids = [int(archivo['id']) for archivo in archivos_enviados]
                archivos_actuales = {
                    archivo.id: archivo
                    for archivo in instance.archivos.filter(id__in=ids)
                }
                orden_maximo = max(
                    (archivo.orden for archivo in instance.archivos.all()),
                    default=0,
                )
                desplazamiento = orden_maximo + len(ids) + 1
                for indice, archivo_id in enumerate(ids, start=1):
                    archivos_actuales[archivo_id].orden = desplazamiento + indice
                    archivos_actuales[archivo_id].save(update_fields=['orden'])

                instance.archivos.exclude(id__in=ids).delete()

                for archivo_enviado, archivo_id in zip(archivos_enviados, ids):
                    archivo = archivos_actuales[archivo_id]
                    archivo.orden = int(archivo_enviado.get('orden', archivo.orden))
                    archivo.save(update_fields=['orden'])

        return instance
