from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from echo.models import Seguidor, Usuario
from echo.serializers.usuario_serializers import (
    RegistroUsuarioSerializer,
    UsuarioDetalleSerializer,
)
from echo.utils.autenticacion import (
    AutenticacionJWT,
    EsDueno,
    RequiereToken,
)
from echo.utils.tokens import generar_token_jwt


class RegistroUsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.filter(activo=True)
    serializer_class = RegistroUsuarioSerializer
    lookup_field = 'nombre_usuario'

    authentication_classes = [AutenticacionJWT]

    def get_serializer_class(self):
        if self.action in ['retrieve', 'list']:
            return UsuarioDetalleSerializer
        return RegistroUsuarioSerializer

    def get_permissions(self):
        if self.action in ['create', 'list', 'retrieve']:
            return [AllowAny()]
        if self.action == 'seguir':
            return [RequiereToken()]
        return [RequiereToken(), EsDueno()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        return Response(
            {
                'mensaje': 'Usuario registrado exitosamente',
                'datos': serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(
            instance,
            data=request.data,
            partial=kwargs.pop('partial', False),
        )
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        nuevo_token = generar_token_jwt(instance)

        return Response(
            {
                'mensaje': 'Perfil actualizado con éxito',
                'datos': serializer.data,
                'token': nuevo_token,
            },
            status=status.HTTP_200_OK,
        )

    def destroy(self, request, *args, **kwargs):
        usuario = self.get_object()
        usuario.activo = False
        usuario.save()

        return Response(
            {'mensaje': 'Usuario eliminado correctamente.'},
            status=status.HTTP_200_OK,
        )

    @action(
        detail=True,
        methods=['post'],
        url_path='seguir',
        permission_classes=[RequiereToken],
    )
    def seguir(self, request, nombre_usuario=None):
        usuario_objetivo = self.get_object()

        if request.user == usuario_objetivo:
            return Response(
                {'error': 'No puedes seguirte a ti mismo.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        relacion = Seguidor.objects.filter(
            seguidor=request.user,
            seguido=usuario_objetivo,
        ).first()

        if relacion:
            relacion.delete()
            esta_siguiendo = False
            mensaje = 'Has dejado de seguir a este usuario.'
        else:
            Seguidor.objects.create(seguidor=request.user, seguido=usuario_objetivo)
            esta_siguiendo = True
            mensaje = 'Ahora sigues a este usuario.'

        datos_usuario = UsuarioDetalleSerializer(
            usuario_objetivo,
            context={'request': request},
        ).data

        return Response(
            {
                'mensaje': mensaje,
                'esta_siguiendo': esta_siguiendo,
                'seguidores_count': datos_usuario['seguidores_count'],
                'seguidos_count': datos_usuario['seguidos_count'],
                'usuario': {
                    'nombre_usuario': usuario_objetivo.nombre_usuario,
                    'tipo_usuario': usuario_objetivo.tipo_usuario,
                },
            },
            status=status.HTTP_200_OK,
        )
