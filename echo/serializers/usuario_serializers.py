from rest_framework import serializers # type: ignore
from django.contrib.auth.hashers import make_password # type: ignore
from django.contrib.auth.password_validation import validate_password as django_validate_password # type: ignore
from django.core.validators import validate_email as django_validate_email # type: ignore
from django.core.exceptions import ValidationError as DjangoValidationError # type: ignore
import re

# Importamos absolutamente todo de tus modelos
from echo.models import *

class RegistroUsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True} 
        }
        read_only_fields = ['activo', 'fecha_creacion']

    def validate_nombre_usuario(self, value):
        patron = r'^[a-zA-Z0-9_]+$'
        if not re.match(patron, value):
            raise serializers.ValidationError("El nombre de usuario solo puede contener letras, números y guiones bajos (_), sin espacios.")
        return value

    def validate_descripcion(self, value):
        if value:
            if len(value) > 250:
                raise serializers.ValidationError("La descripción no puede superar los 250 caracteres.")
            patron = r'^[a-zA-Z0-9áéíóúÁÉÍÓÚñÑ\s]+$'
            if not re.match(patron, value):
                raise serializers.ValidationError("La descripción solo puede contener letras y números.")
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
        # PROTECCIÓN GLOBAL CONTRA SCRIPTS (XSS)
        for campo, valor in data.items():
            if isinstance(valor, str) and ('<' in valor or '>' in valor):
                raise serializers.ValidationError({campo: "No se permiten caracteres especiales como < o > por seguridad."})

        if 'nombre' in data and data['nombre']:
            data['nombre'] = data['nombre'].strip()
        if 'apellido' in data and data['apellido']:
            data['apellido'] = data['apellido'].strip()

        tipo = data.get('tipo_usuario', getattr(self.instance, 'tipo_usuario', None))

        if tipo == 'empresarial':
            errores = {}
            if not data.get('nombre_negocio') and not getattr(self.instance, 'nombre_negocio', None):
                errores['nombre_negocio'] = "El nombre del negocio es obligatorio para perfiles empresariales."
            if not data.get('telefono') and not getattr(self.instance, 'telefono', None):
                errores['telefono'] = "El teléfono es obligatorio para perfiles empresariales."
            if not data.get('direccion') and not getattr(self.instance, 'direccion', None):
                errores['direccion'] = "La dirección es obligatoria para perfiles empresariales."
            
            if errores:
                raise serializers.ValidationError(errores)

            data['nombre'] = None
            data['apellido'] = None

        if tipo == 'normal':
            errores = {}
            if not data.get('nombre') and not getattr(self.instance, 'nombre', None):
                errores['nombre'] = "El nombre es obligatorio para ciudadanos."
            if not data.get('apellido') and not getattr(self.instance, 'apellido', None):
                errores['apellido'] = "El apellido es obligatorio para ciudadanos."
            
            if errores:
                raise serializers.ValidationError(errores)

            data['nombre_negocio'] = None
            data['direccion'] = None

        if tipo not in ['normal', 'empresarial']:
            raise serializers.ValidationError({"tipo_usuario": "Tipo de usuario no válido."})

        return data

    def create(self, validated_data):
        validated_data['password'] = make_password(validated_data['password'])
        return super().create(validated_data)

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            validated_data['password'] = make_password(validated_data['password'])
        return super().update(instance, validated_data)