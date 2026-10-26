import re

from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password as django_validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email as django_validate_email
from django.utils.html import strip_tags
from rest_framework import serializers

from echo.models import Calificacion, Seguidor, Usuario


class CalificacionSerializer(serializers.ModelSerializer):
    usuario = serializers.SerializerMethodField()

    class Meta:
        model = Calificacion
        fields = ['id', 'puntuacion', 'descripcion', 'fecha_creacion', 'usuario']

    def get_usuario(self, obj):
        return {
            'nombre_usuario': obj.usuario_califica.nombre_usuario,
            'foto_perfil': obj.usuario_califica.foto_perfil,
        }


class RegistroUsuarioSerializer(serializers.ModelSerializer):
    confirmar_password = serializers.CharField(write_only=True, required=False)

    class Meta:
        model = Usuario
        fields = '__all__'
        extra_kwargs = {'password': {'write_only': True}}
        read_only_fields = ['activo', 'fecha_creacion']

    def validate_nombre_usuario(self, value):
        patron = r'^[a-zA-Z0-9_]+$'
        if not re.match(patron, value):
            raise serializers.ValidationError(
                'El nombre de usuario solo puede contener letras, números y guiones bajos (_), sin espacios.'
            )
        return value

    def validate_descripcion(self, value):
        if value and len(value) > 250:
            raise serializers.ValidationError('La descripción no puede superar los 250 caracteres.')
        return value

    def validate_telefono(self, value):
        if value:
            if not value.isdigit():
                raise serializers.ValidationError('El teléfono debe contener únicamente números.')
            if len(value) != 10:
                raise serializers.ValidationError('El teléfono debe tener exactamente 10 dígitos.')
        return value

    def validate_password(self, value):
        try:
            django_validate_password(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(list(error.messages))
        return value

    def validate_email(self, value):
        email_limpio = value.lower().strip()
        try:
            django_validate_email(email_limpio)
        except DjangoValidationError:
            raise serializers.ValidationError('El correo electrónico no tiene un formato válido.')
        return email_limpio

    def validate(self, data):
        if 'password' in data:
            if 'confirmar_password' not in data:
                raise serializers.ValidationError(
                    {'confirmar_password': 'Debes confirmar la contraseña.'}
                )
            if data['password'] != data['confirmar_password']:
                raise serializers.ValidationError({'password': 'Las contraseñas no coinciden.'})
            data.pop('confirmar_password')

        for campo, valor in data.items():
            if campo != 'password' and isinstance(valor, str):
                data[campo] = strip_tags(valor)

        tipo = data.get('tipo_usuario', getattr(self.instance, 'tipo_usuario', None))
        if 'nombre' in data:
            data['nombre'] = data['nombre'].strip()
        if 'apellido' in data:
            data['apellido'] = data['apellido'].strip()

        if tipo == 'empresarial':
            errores = {}
            if not data.get('nombre_negocio', getattr(self.instance, 'nombre_negocio', None)):
                errores['nombre_negocio'] = 'Obligatorio para empresas.'
            if not data.get('telefono', getattr(self.instance, 'telefono', None)):
                errores['telefono'] = 'Obligatorio para empresas.'
            if not data.get('direccion', getattr(self.instance, 'direccion', None)):
                errores['direccion'] = 'Obligatorio para empresas.'
            if errores:
                raise serializers.ValidationError(errores)
            data['nombre'] = None
            data['apellido'] = None
        elif tipo == 'normal':
            errores = {}
            if not data.get('nombre', getattr(self.instance, 'nombre', None)):
                errores['nombre'] = 'Obligatorio para ciudadanos.'
            if not data.get('apellido', getattr(self.instance, 'apellido', None)):
                errores['apellido'] = 'Obligatorio para ciudadanos.'
            if errores:
                raise serializers.ValidationError(errores)
            data['nombre_negocio'] = None
            data['direccion'] = None
        else:
            raise serializers.ValidationError({'tipo_usuario': 'Tipo de usuario no válido.'})

        return data

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        return super().update(instance, validated_data)


class UsuarioDetalleSerializer(serializers.ModelSerializer):
    resenas = serializers.SerializerMethodField()
    seguidores_count = serializers.SerializerMethodField()
    seguidos_count = serializers.SerializerMethodField()
    esta_siguiendo = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            'id', 'email', 'nombre_usuario', 'password', 'tipo_usuario',
            'fecha_creacion', 'activo', 'foto_perfil', 'nombre', 'apellido',
            'nombre_negocio', 'descripcion', 'direccion', 'telefono',
            'seguidores_count', 'seguidos_count', 'esta_siguiendo', 'resenas',
        ]
        extra_kwargs = {'password': {'write_only': True}}
        read_only_fields = ['activo', 'fecha_creacion']

    def get_resenas(self, obj):
        calificaciones = obj.calificaciones_recibidas.select_related(
            'usuario_califica'
        ).order_by('-fecha_creacion', '-id')
        return CalificacionSerializer(calificaciones, many=True).data

    def get_seguidores_count(self, obj):
        return obj.seguidores.count()

    def get_seguidos_count(self, obj):
        return obj.siguiendo.count()

    def get_esta_siguiendo(self, obj):
        request = self.context.get('request')
        if not request or not hasattr(request, 'user'):
            return False

        usuario_actual = request.user
        if hasattr(usuario_actual, 'is_anonymous') and usuario_actual.is_anonymous:
            return False
        if not hasattr(usuario_actual, 'pk'):
            return False

        return Seguidor.objects.filter(
            seguidor_id=usuario_actual.pk,
            seguido=obj,
        ).exists()
