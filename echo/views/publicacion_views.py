from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from echo.models import Comentario, Like, Publicacion, Seguidor
from echo.serializers.publicacion_serializers import (
    ComentarioSerializer,
    CrearPublicacionserializer,
)
from echo.utils.autenticacion import AutenticacionJWT, EsDueno, RequiereToken


class PaginacionPublicaciones(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'tamano'
    max_page_size = 50


class PublicacionViewSet(viewsets.ModelViewSet):
    serializer_class = CrearPublicacionserializer
    authentication_classes = [AutenticacionJWT]
    pagination_class = PaginacionPublicaciones

    def get_queryset(self):
        publicaciones_activas = (
            Publicacion.objects.filter(activo=True)
            .select_related('usuario')
            .prefetch_related(
                'archivos',
                'likes_publicacion__usuario',
                'comentarios_publicacion__usuario',
            )
        )

        if self.action != 'list':
            return publicaciones_activas

        usuario_perfil = self.request.query_params.get('usuario')
        if usuario_perfil:
            return publicaciones_activas.filter(
                usuario__nombre_usuario=usuario_perfil,
            ).order_by('-fecha_creacion')

        usuario_likes = self.request.query_params.get('like')
        if usuario_likes:
            return publicaciones_activas.filter(
                likes_publicacion__usuario__nombre_usuario=usuario_likes,
            ).distinct().order_by('-fecha_creacion')

        usuario_actual = self.request.user
        if not hasattr(usuario_actual, 'tipo_usuario'):
            return publicaciones_activas.order_by('?')

        ids_usuarios_seguidos = Seguidor.objects.filter(
            seguidor=usuario_actual,
        ).values_list('seguido_id', flat=True)
        if ids_usuarios_seguidos.exists():
            publicaciones_seguidas = publicaciones_activas.filter(
                usuario_id__in=ids_usuarios_seguidos,
            ).order_by('-fecha_creacion')
            if publicaciones_seguidas.exists():
                return publicaciones_seguidas

        return publicaciones_activas.order_by('?')

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        if self.action == 'dar_like':
            return [RequiereToken()]
        return [RequiereToken(), EsDueno()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(usuario=request.user)
        return Response(
            {
                'mensaje': 'Publicación creada correctamente',
                'datos': serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    def destroy(self, request, *args, **kwargs):
        publicacion = self.get_object()
        publicacion.activo = False
        publicacion.save(update_fields=['activo'])
        return Response(
            {'mensaje': 'Publicación eliminada correctamente.'},
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='like')
    def dar_like(self, request, pk=None):
        publicacion = self.get_object()
        usuario = request.user

        if publicacion.usuario_id == usuario.id:
            return Response(
                {'error': 'No puedes darle like a tu propia publicación.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        like_existente = Like.objects.filter(
            usuario=usuario,
            publicacion=publicacion,
        ).first()
        if like_existente:
            like_existente.delete()
        else:
            Like.objects.create(usuario=usuario, publicacion=publicacion)

        return Response(status=status.HTTP_204_NO_CONTENT)


class ComentarioViewSet(viewsets.ModelViewSet):
    serializer_class = ComentarioSerializer
    authentication_classes = [AutenticacionJWT]

    def get_queryset(self):
        return (
            Comentario.objects.filter(
                activo=True,
                publicacion__activo=True,
                usuario__activo=True,
            )
            .select_related('usuario', 'publicacion', 'comentario_padre')
        )

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [RequiereToken(), EsDueno()]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(usuario=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        comentario = self.get_object()
        comentario.activo = False
        comentario.save(update_fields=['activo'])
        return Response(status=status.HTTP_204_NO_CONTENT)
