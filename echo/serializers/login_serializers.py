from rest_framework import serializers # type: ignore

class LoginSerializer(serializers.Serializer):
    identificador = serializers.CharField(required=True)
    password = serializers.CharField(required=True, write_only=True)