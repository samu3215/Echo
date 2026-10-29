from rest_framework import serializers
from django.utils.html import strip_tags
from ..models import *
from .publicacion_serializers import UsuarioBasicoSerializer

class CalificacionSerializer(serializers.ModelSerializer):
    usuario_califica = UsuarioBasicoSerializer(read_only=True)

    class Meta:
        model = Calificacion
        fields = ['id', 'puntuacion', 'descripcion', 'fecha_creacion', 'usuario_califica', 'usuario_calificado']
        read_only_fields = ['id', 'fecha_creacion', 'usuario_califica']

    def validate_descripcion(self, value):
        if value:
            valor_limpio = strip_tags(value.strip())
            if len(valor_limpio) > 500:
                raise serializers.ValidationError("La descripción de la calificación no puede superar los 500 caracteres.")
            return valor_limpio
        return value

    def validate(self, data):
        request = self.context.get('request')
        usuario_actual = request.user
        
        # Extraemos el usuario calificado del request (al crear) o de la base de datos (al editar)
        usuario_calificado = data.get('usuario_calificado')
        if not usuario_calificado and self.instance:
            usuario_calificado = self.instance.usuario_calificado

        if usuario_calificado:
            if usuario_actual == usuario_calificado:
                raise serializers.ValidationError("No puedes calificarte a ti mismo.")
            
            if usuario_calificado.tipo_usuario != 'empresarial':
                raise serializers.ValidationError("Solo puedes calificar cuentas empresariales.")

        # Verificamos reseñas duplicadas SOLO cuando se está creando una nueva (self.instance is None)
        if self.instance is None:
            if Calificacion.objects.filter(usuario_califica=usuario_actual, usuario_calificado=usuario_calificado, activo=True).exists():
                raise serializers.ValidationError("Ya has dejado una reseña activa para este negocio.")
        return data