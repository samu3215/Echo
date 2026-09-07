from rest_framework import viewsets, status # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework.permissions import AllowAny # type: ignore

from echo.models import *
from echo.serializers.usuario_serializers import *
from echo.utils.autenticacion import *

class RegistroUsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.filter(activo=True)
    serializer_class = RegistroUsuarioSerializer
    lookup_field = 'nombre_usuario'

    authentication_classes = [AutenticacionJWT]

    def get_permissions(self):
       
        if self.action in ['create', 'list', 'retrieve']:
            return [AllowAny()]
        
        return [RequiereToken(), EsDuenoDelPerfil()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        return Response(
            {
                "mensaje": "Usuario registrado exitosamente",
                "datos": serializer.data
            }, 
            status=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):
        usuario = self.get_object()
        usuario.activo = False
        usuario.save()
        return Response(
            {"mensaje": "Usuario desactivado correctamente."}, 
            status=status.HTTP_204_NO_CONTENT
        )