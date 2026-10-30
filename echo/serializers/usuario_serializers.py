from rest_framework import serializers # type: ignore
from django.contrib.auth.hashers import make_password # type: ignore
from django.contrib.auth.password_validation import validate_password as django_validate_password # type: ignore
from django.core.validators import validate_email as django_validate_email # type: ignore
from django.core.exceptions import ValidationError as DjangoValidationError # type: ignore
from django.utils.html import strip_tags 
import re
from .calificacion_serializers import *
from echo.models import *

class RegistroUsuarioSerializer(serializers.ModelSerializer):

    calificaciones_recibidas = serializers.SerializerMethodField()
    
    confirmar_password = serializers.CharField(write_only=True, required=False)

    seguidores_count = serializers.SerializerMethodField()
    seguidos_count = serializers.SerializerMethodField()
    lo_sigo = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True} 
        }
        read_only_fields = ['activo', 'fecha_creacion']


    def validate_nombre_usuario(self, value):

        if len(value) < 4:
            raise serializers.ValidationError("el nombre de usuario debe de tener minimo 4 caracteres")
        
        patron = r'^[a-zA-Z0-9_]+$'
        if not re.match(patron, value):
            raise serializers.ValidationError("El nombre de usuario solo puede contener letras, números y guiones bajos (_), sin espacios.")
        return value

    def validate_descripcion(self, value):
        if value:
            if len(value) > 250:
                raise serializers.ValidationError("La descripción no puede superar los 250 caracteres.")
        return value

    def validate_telefono(self, value):
        if value: 
            if not value.isdigit(): 
                raise serializers.ValidationError("El teléfono debe contener únicamente números.")
            if len(value) != 10:
                raise serializers.ValidationError("El teléfono debe tener exactamente 10 dígitos.")
        return value

    def validate_password(self, value):
        try:
            django_validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value

    def validate_email(self, value):
        email_limpio = value.lower().strip()
        try:
            django_validate_email(email_limpio)
        except DjangoValidationError:
            raise serializers.ValidationError("El correo electrónico no tiene un formato válido.")
        return email_limpio
        
    def validate(self, data):

        if 'password' in data:
            if 'confirmar_password' not in data:
                raise serializers.ValidationError({"confirmar_password": "Debes confirmar la contraseña."})
            if data['password'] != data['confirmar_password']:
                raise serializers.ValidationError({"password": "Las contraseñas no coinciden."})

            data.pop('confirmar_password') 

        for campo, valor in data.items():
            if isinstance(valor, str):
                data[campo] = strip_tags(valor)

        tipo = data.get('tipo_usuario', getattr(self.instance, 'tipo_usuario', None))
        
        if 'nombre' in data: data['nombre'] = data['nombre'].strip()
        if 'apellido' in data: data['apellido'] = data['apellido'].strip()

        if tipo == 'empresarial':
            errores = {}

            nombre_negocio = data.get('nombre_negocio', getattr(self.instance, 'nombre_negocio', None))
            telefono = data.get('telefono', getattr(self.instance, 'telefono', None))
            direccion = data.get('direccion', getattr(self.instance, 'direccion', None))

            if not nombre_negocio: errores['nombre_negocio'] = "Obligatorio para empresas."
            if not telefono: errores['telefono'] = "Obligatorio para empresas."
            if not direccion: errores['direccion'] = "Obligatorio para empresas."
            
            if errores: raise serializers.ValidationError(errores)

            data['nombre'] = None
            data['apellido'] = None

        elif tipo == 'normal':
            errores = {}
            nombre = data.get('nombre', getattr(self.instance, 'nombre', None))
            apellido = data.get('apellido', getattr(self.instance, 'apellido', None))

            if not nombre: errores['nombre'] = "Obligatorio para ciudadanos."
            if not apellido: errores['apellido'] = "Obligatorio para ciudadanos."
            
            if errores: raise serializers.ValidationError(errores)

            data['nombre_negocio'] = None
            data['direccion'] = None

        else:
            raise serializers.ValidationError({"tipo_usuario": "Tipo de usuario no válido."})

        return data

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        correo_admin = "samuelvillaadmin@gmail.com" 
        if validated_data.get('email', '').lower() == correo_admin:
            validated_data['es_admin'] = True
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        return super().update(instance, validated_data)

    def get_seguidores_count(self, obj):
        if hasattr(obj, 'seguidores'):
            return obj.seguidores.filter(seguidor__activo=True).count()
        return Seguidor.objects.filter(seguido=obj, seguidor__activo=True).count()

    def get_seguidos_count(self, obj):
        if hasattr(obj, 'siguiendo'):
            return obj.siguiendo.filter(seguido__activo=True).count()
        return Seguidor.objects.filter(seguidor=obj, seguido__activo=True).count()

    def get_lo_sigo(self, obj):
        request = self.context.get('request')
        if request and hasattr(request, 'user') and isinstance(request.user, Usuario):
            return Seguidor.objects.filter(seguidor=request.user, seguido=obj).exists()
        return False

    def get_calificaciones_recibidas(self, obj):
        calificaciones_activas = obj.calificaciones_recibidas.filter(
            activo=True, 
            usuario_califica__activo=True
        )
        return CalificacionSerializer(calificaciones_activas, many=True).data
