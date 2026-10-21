from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination 
from ..serializers.publicacion_serializers import *
from django.db.models import Case, When, Value, IntegerField
from ..models import *

from ..utils.autenticacion import *

class PaginacionPublicaciones(PageNumberPagination):
    page_size = 10 
    page_size_query_param = 'tamano' 
    max_page_size = 50 

class PublicacionViewSet(viewsets.ModelViewSet):
    serializer_class = PublicacioSeraializer
    authentication_classes = [AutenticacionJWT]
    pagination_class = PaginacionPublicaciones

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]

        if self.action == 'dar_like':
            return [RequiereToken()]
        
        return [RequiereToken(), EsDueno()] 

    def get_queryset(self):
        publicaciones_activas = Publicacion.objects.filter(activo=True).select_related('usuario')

        usuario_perfil = self.request.query_params.get('usuario', None)
        if usuario_perfil:
            return publicaciones_activas.filter(usuario__nombre_usuario=usuario_perfil).order_by('-fecha_creacion')

        usuario_likes = self.request.query_params.get('like', None)
        if usuario_likes:
            
            return publicaciones_activas.filter(
                likes_publicacion__usuario__nombre_usuario=usuario_likes
            ).order_by('-fecha_creacion')


        ids_usuarios_seguidos = []
        if isinstance(self.request.user, Usuario):
            ids_usuarios_seguidos = Seguidor.objects.filter(seguidor=self.request.user).values_list('seguido_id', flat=True)

        return publicaciones_activas.annotate(
            prioridad=Case(
                When(usuario__tipo_usuario='empresarial', then=Value(0)),
                When(usuario__id__in=ids_usuarios_seguidos, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        ).order_by('prioridad', '-fecha_creacion')

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(usuario=request.user)
        return Response({"mensaje": "Publicación creada correctamente", "datos": serializer.data}, status=status.HTTP_201_CREATED)

    def destroy(self, request, *args, **kwargs):
        publicacion = self.get_object()
        publicacion.activo = False
        publicacion.save()
        return Response({"mensaje": "Publicación eliminada correctamente."}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='like')
    def dar_like(self, request, pk=None):
        publicacion = self.get_object() 
        usuario = request.user

        if publicacion.usuario.id == usuario.id:
            return Response(
                {"error": "No puedes darle like a tu propia publicación."}, 
                status=status.HTTP_403_FORBIDDEN
            )

        like_existente = Like.objects.filter(usuario=usuario, publicacion=publicacion).first()
        if like_existente:
            like_existente.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        Like.objects.create(usuario=usuario, publicacion=publicacion)
        return Response(status=status.HTTP_204_NO_CONTENT)



class ComentarioViewSet(viewsets.ModelViewSet):

    queryset = Comentario.objects.filter(activo=True)
    serializer_class = ComentarioSerializer
    authentication_classes = [AutenticacionJWT]

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
        comentario.save()
        return Response(status=status.HTTP_204_NO_CONTENT)