from rest_framework import serializers
from django.utils.html import strip_tags
from ..models import *


class UsuarioBasicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ['id', 'nombre_usuario', 'foto_perfil', 'tipo_usuario', 'nombre', 'apellido', 'nombre_negocio']
        read_only_fields = fields


class Likeserializer(serializers.ModelSerializer):
    usuario = UsuarioBasicoSerializer(read_only=True)

    class Meta:
        model = Like
        fields = ['id', 'usuario', 'fecha']
        read_only_fields = ['id', 'usuario', 'fecha']
    
class ArchivoPublicacionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivoPublicacion
        fields = ['id', 'url_media', 'tipo_media', 'orden']
        read_only_fields = ['id']


class ComentarioSerializer(serializers.ModelSerializer):
    usuario = UsuarioBasicoSerializer(read_only=True)

    class Meta:
        model = Comentario
        fields = [
            'id', 'contenido', 'fecha_creacion', 'fecha_actualizacion', 
            'activo', 'usuario', 'publicacion', 'comentario_padre']
        
        read_only_fields = ['id', 'fecha_creacion', 'fecha_actualizacion', 'activo', 'usuario']

    def validate_contenido(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("El comentario no puede estar vacío.")
        return strip_tags(value.strip())

    def validate(self, data):
        publicacion = data.get('publicacion')
        if publicacion and not publicacion.comentarios_activados:
            raise serializers.ValidationError({"publicacion": "Los comentarios están desactivados para esta publicación."})
        return data

class PublicacioSeraializer(serializers.ModelSerializer):
    archivos = ArchivoPublicacionSerializer(many=True, required=False)
    likes_publicacion = Likeserializer(many=True, read_only=True)
    comentarios_publicacion = ComentarioSerializer(many=True, read_only=True)

    usuario = UsuarioBasicoSerializer(read_only=True)
    
    class Meta:
        model = Publicacion
        fields = [
            'id', 'descripcion', 'comentarios_activados', 
            'fecha_creacion', 'fecha_actualizacion', 
            'activo', 'usuario', 'archivos', 'likes_publicacion', 'comentarios_publicacion'
        ]
        
        read_only_fields = [
            'id', 'fecha_creacion', 'fecha_actualizacion', 
            'activo', 'usuario', 'likes_publicacion', 'comentarios_publicacion'
        ]

    def validate(self, data):
 
        for campo, valor in data.items():
            if isinstance(valor, str):
                data[campo] = strip_tags(valor)


        descripcion = data.get('descripcion')
        if isinstance(descripcion, str):
            descripcion = descripcion.strip()  
            data['descripcion'] = descripcion  

        if self.instance is None:

            archivos = self.initial_data.get('archivos', [])
            
            if len(archivos) > 8:
                raise serializers.ValidationError({"archivos": "El límite máximo es de 8 archivos por publicación."})
            if not descripcion and not archivos:
                raise serializers.ValidationError("La publicación debe tener al menos una descripción o un archivo multimedia.")
        else:

            archivos_enviados = self.initial_data.get('archivos', [])
            if archivos_enviados and isinstance(archivos_enviados, list):
                for archivo in archivos_enviados:
 
                    if 'id' not in archivo:
                        raise serializers.ValidationError({"archivos": "No está permitido agregar nuevos archivos al editar."})

            descripcion_final = data.get('descripcion', self.instance.descripcion)
            tiene_archivos = self.instance.archivos.exists() 
            
            if not descripcion_final and not tiene_archivos:
                raise serializers.ValidationError("No puedes dejar la publicación vacía. Escribe una descripción o conserva los archivos.")
            
        return data

    def create(self, validated_data):
        archivos_data = validated_data.pop('archivos', [])
        publicacion = Publicacion.objects.create(**validated_data)
        
        for archivo in archivos_data:
            ArchivoPublicacion.objects.create(publicacion=publicacion, **archivo)
            
        return publicacion
    
    def update(self, instance, validated_data):

        instance.descripcion = validated_data.get('descripcion', instance.descripcion)
        instance.comentarios_activados = validated_data.get('comentarios_activados', instance.comentarios_activados)
        instance.save()

        archivos_data = self.initial_data.get('archivos', None)
        if archivos_data and isinstance(archivos_data, list):
            for archivo in archivos_data:
                archivo_id = archivo.get('id')
                if archivo_id:
                    ArchivoPublicacion.objects.filter(
                        id=archivo_id, 
                        publicacion=instance
                    ).update(orden=1000 + int(archivo_id)) 


            for archivo in archivos_data:
                archivo_id = archivo.get('id')
                nuevo_orden = archivo.get('orden')
                
                if archivo_id and nuevo_orden is not None:
                    ArchivoPublicacion.objects.filter(
                        id=archivo_id, 
                        publicacion=instance
                    ).update(orden=nuevo_orden)

        return instance