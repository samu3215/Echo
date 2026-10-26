from rest_framework import serializers

from echo.models import Publicacion



class CrearPublicacionserializer(serializers.ModelSerializer):

    class meta:
        model = Publicacion
        fields = '__all__'
        read_only_fields = ['activo', 'fecha_creacion','fecha_actualizacion']