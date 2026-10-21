from rest_framework import serializers
from django.utils.html import strip_tags
from ..models import *
from .publicacion_serializers import UsuarioBasicoSerializer

class ComunidadSerializer(serializers.ModelSerializer):
    usuario = UsuarioBasicoSerializer(read_only=True)
    total_miembros = serializers.SerializerMethodField()
    estoy_unido = serializers.SerializerMethodField()

    class Meta:
        model = Comunidad
        fields = [
            'id', 'nombre', 'descripcion', 'categoria', 
            'foto_comunidad', 'activo', 'usuario', 'fecha_creacion', 'total_miembros', 'estoy_unido'
        ]
        read_only_fields = ['id', 'activo', 'usuario', 'fecha_creacion']

    def get_total_miembros(self, obj):
        return obj.miembros.count()

    def get_estoy_unido(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and isinstance(request.user, Usuario):
            return obj.miembros.filter(usuario=request.user).exists()
        return False

    def validate(self, data):
        for campo, valor in data.items():
            if isinstance(valor, str):
                valor_limpio = strip_tags(valor.strip())
                data[campo] = valor_limpio
                
        if 'nombre' in data and not data['nombre']:
            raise serializers.ValidationError({"nombre": "El nombre de la comunidad no puede estar vacío."})

        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            usuario_actual = request.user
            categoria_seleccionada = data.get('categoria')

           
            if categoria_seleccionada == 'negocios' and usuario_actual.tipo_usuario != 'empresarial':
                raise serializers.ValidationError({
                    "categoria": "La categoría 'Negocios' es exclusiva para cuentas empresariales."
                })
            
            
            if usuario_actual.tipo_usuario == 'empresarial' and categoria_seleccionada != 'negocios':
                raise serializers.ValidationError({
                    "categoria": "Las cuentas empresariales solo pueden crear comunidades bajo la categoría de 'Negocios'."
                })
            
        return data


class ArchivoMensajeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivoMensaje
        fields = ['id', 'url_media', 'tipo_media']
        read_only_fields = ['id']


class MensajeComunidadSerializer(serializers.ModelSerializer):
    usuario = UsuarioBasicoSerializer(read_only=True)

    archivos = ArchivoMensajeSerializer(many=True, required=False)

    class Meta:
        model = MensajeComunidad
        fields = [
            'id', 'contenido', 'archivos', 'fecha_envio', 'fecha_actualizacion', 
            'activo', 'usuario', 'comunidad', 'publicacion_reenviada', 'mensaje_respondido'
        ]
        read_only_fields = ['id', 'fecha_envio', 'fecha_actualizacion', 'activo', 'usuario']

    def validate(self, data):

        if 'contenido' in data and isinstance(data['contenido'], str):
            data['contenido'] = strip_tags(data['contenido'].strip())

        contenido = data.get('contenido')
        publicacion = data.get('publicacion_reenviada')
        
        archivos = self.initial_data.get('archivos', [])

        if len(archivos) > 4:
            raise serializers.ValidationError({"archivos": "Solo puedes enviar hasta 4 archivos por mensaje."})

        if not contenido and not archivos and not publicacion:
            raise serializers.ValidationError("El mensaje no puede estar vacío. Debes enviar texto, un archivo o una publicación.")
            
        return data

    def create(self, validated_data):
        archivos_data = validated_data.pop('archivos', [])
        mensaje = MensajeComunidad.objects.create(**validated_data)
        
        for archivo in archivos_data:
            ArchivoMensaje.objects.create(mensaje=mensaje, **archivo)
            
        return mensaje