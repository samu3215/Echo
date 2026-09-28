from django.contrib.auth.hashers import check_password # type: ignore
from django.db.models import Q # type: ignore
from rest_framework.views import APIView # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework import status # type: ignore

from echo.models import *
from echo.serializers.login_serializers import *
from echo.utils.tokens import *

class LoginAPIView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        if serializer.is_valid():
            identificador = serializer.validated_data['identificador']
            password = serializer.validated_data['password']

            try:
                usuario = Usuario.objects.get(
                    Q(email=identificador) | Q(nombre_usuario=identificador)
                )
            except Usuario.DoesNotExist:
                return Response({"error": "El usuario no existe."}, status=status.HTTP_401_UNAUTHORIZED)

            if not usuario.activo:
                return Response({"error": "Esta cuenta ha sido desactivada."}, status=status.HTTP_403_FORBIDDEN)

            if not check_password(password, usuario.password):
                return Response({"error": "Datos incorrectos."}, status=status.HTTP_401_UNAUTHORIZED)


            token = generar_token_jwt(usuario)

            return Response({
                "mensaje": "Login exitoso",
                "token": token
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)