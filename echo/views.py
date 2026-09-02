import jwt
import datetime
from django.conf import settings
from django.contrib.auth.hashers import check_password
from django.shortcuts import render
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import *
from .serializers import *

class UsuarioViewSet(viewsets.ModelViewSet):
    
    queryset = Usuario.objects.filter(activo=True)
    serializer_class = UsuarioSerializer

    def destroy(self, request, *args, **kwargs):
        
        usuario = self.get_object()
        usuario.activo = False
        usuario.save()
        return Response(
            {"mensaje": "Usuario desactivado correctamente."}, 
            status=status.HTTP_204_NO_CONTENT
        )
# Create your views here.


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
                return Response({"error": "Credenciales inválidas."}, status=status.HTTP_401_UNAUTHORIZED)

            if not usuario.activo:
                return Response({"error": "Esta cuenta ha sido desactivada."}, status=status.HTTP_403_FORBIDDEN)

            if not check_password(password, usuario.password):
                return Response({"error": "Credenciales inválidas."}, status=status.HTTP_401_UNAUTHORIZED)


            payload = {
                'user_id': usuario.id,
                'nombre_usuario': usuario.nombre_usuario,
                'tipo_usuario': usuario.tipo_usuario,
                'exp': datetime.datetime.utcnow() + datetime.timedelta(days=1), # Expira en 1 día
                'iat': datetime.datetime.utcnow()
            }
            
            token = jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

            return Response({
                "mensaje": "Login exitoso",
                "token": token
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)