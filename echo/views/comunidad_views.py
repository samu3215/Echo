from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.decorators import action
from django.db.models import Q
from django.db.models import Q, Case, When, Value, IntegerField
from .publicacion_views import PaginacionPublicaciones
from ..serializers.comunidad_serializers import *
from ..models import *
from ..utils.autenticacion import *

class ComunidadViewSet(viewsets.ModelViewSet):
    serializer_class = ComunidadSerializer
    authentication_classes = [AutenticacionJWT]
    pagination_class = PaginacionPublicaciones

    def get_permissions(self):

        if self.action in ['list', 'retrieve', 'miembros']:
            return [AllowAny()]

        if self.action in ['miembro', 'expulsar', 'transferir_propiedad']:
            return [RequiereToken()]

        return [RequiereToken(), EsDueno()]

    def get_queryset(self):
        comunidades_activas = Comunidad.objects.filter(activo=True).select_related('usuario')

        usuario_creador = self.request.query_params.get('usuario', None)
        if usuario_creador:
            return comunidades_activas.filter(usuario__nombre_usuario=usuario_creador).order_by('-fecha_creacion')

        mostrar_unidas = self.request.query_params.get('unidas', None)
        if mostrar_unidas == 'true' and isinstance(self.request.user, Usuario):
            return comunidades_activas.filter(miembros__usuario=self.request.user).order_by('-fecha_creacion')
            
        categoria = self.request.query_params.get('categoria', None)
        if categoria:
            return comunidades_activas.filter(categoria=categoria).order_by('-fecha_creacion')
            
        buscar = self.request.query_params.get('buscar', None)
        if buscar:
            comunidades_activas = comunidades_activas.filter(
                Q(nombre__icontains=buscar) | Q(descripcion__icontains=buscar)
            )

        return comunidades_activas.annotate(
            prioridad=Case(
                When(usuario__tipo_usuario='empresarial', then=Value(0)),
                default=Value(1),
                output_field=IntegerField(),
            )
        ).order_by('prioridad', '-fecha_creacion')

    def perform_create(self, serializer):
        comunidad = serializer.save(usuario=self.request.user)
        UsuarioComunidad.objects.create(usuario=self.request.user, comunidad=comunidad)

    def destroy(self, request, *args, **kwargs):
        comunidad = self.get_object()
        comunidad.activo = False
        comunidad.save()
        return Response(status=status.HTTP_204_NO_CONTENT)

    # accion unirse y salirse de una comunidad
    @action(detail=True, methods=['post'], url_path='miembro')
    def miembro(self, request, pk=None):
        comunidad = self.get_object()
        usuario = request.user

        membresia_existente = UsuarioComunidad.objects.filter(usuario=usuario, comunidad=comunidad).first()
        
        if membresia_existente:
            if comunidad.usuario.id == usuario.id:
                return Response(
                    {"error": "No puedes abandonar la comunidad siendo el administrador. Transfiere la propiedad a otra persona primero."}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            membresia_existente.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        
        UsuarioComunidad.objects.create(usuario=usuario, comunidad=comunidad)
        return Response(status=status.HTTP_201_CREATED)

    # accion listar los miembros
    @action(detail=True, methods=['get'], url_path='miembros')
    def miembros(self, request, pk=None):
        comunidad = self.get_object()
        miembros_relacion = UsuarioComunidad.objects.filter(comunidad=comunidad).select_related('usuario')
        
        datos_miembros = []
        for rel in miembros_relacion:
            datos_miembros.append({
                "id": rel.usuario.id,
                "nombre_usuario": rel.usuario.nombre_usuario,
                "foto_perfil": rel.usuario.foto_perfil,
                "es_administrador": rel.usuario.id == comunidad.usuario.id,
                "tipo_usuario": rel.usuario.tipo_usuario
            })
            
        return Response(datos_miembros, status=status.HTTP_200_OK)

    # accion expulsar a un miembro
    @action(detail=True, methods=['post'], url_path='expulsar')
    def expulsar(self, request, pk=None):
        comunidad = self.get_object()
        
        if request.user.id != comunidad.usuario.id:
            return Response({"error": "Solo el administrador puede expulsar miembros."}, status=status.HTTP_403_FORBIDDEN)
            
        usuario_a_expulsar = request.data.get('usuario_id')
        if not usuario_a_expulsar:
            return Response({"error": "Debes especificar el usuario a expulsar."}, status=status.HTTP_400_BAD_REQUEST)
            
        if int(usuario_a_expulsar) == comunidad.usuario.id:
            return Response({"error": "No puedes expulsarte a ti mismo."}, status=status.HTTP_400_BAD_REQUEST)
            
        UsuarioComunidad.objects.filter(comunidad=comunidad, usuario_id=usuario_a_expulsar).delete()
        return Response({"mensaje": "Usuario expulsado de la comunidad."}, status=status.HTTP_200_OK)

    # accion cambiar dueño de la comunidad
    @action(detail=True, methods=['patch'], url_path='transferir-propiedad')
    def transferir_propiedad(self, request, pk=None):
        comunidad = self.get_object()
        
        if request.user.id != comunidad.usuario.id:
            return Response({"error": "Solo el administrador actual puede transferir la propiedad."}, status=status.HTTP_403_FORBIDDEN)
            
        nuevo_dueno_id = request.data.get('nuevo_dueno_id')
        if not nuevo_dueno_id:
            return Response({"error": "Debes especificar al nuevo dueño."}, status=status.HTTP_400_BAD_REQUEST)
            
        membresia_nuevo_dueno = UsuarioComunidad.objects.filter(comunidad=comunidad, usuario_id=nuevo_dueno_id).select_related('usuario').first()
        if not membresia_nuevo_dueno:
            return Response({"error": "El nuevo administrador debe ser miembro de la comunidad primero."}, status=status.HTTP_400_BAD_REQUEST)
            
        comunidad.usuario_id = nuevo_dueno_id

        if membresia_nuevo_dueno.usuario.tipo_usuario == 'empresarial':
            return Response({"error": "Un usuario empresarial no puede ser designado como dueño de la comunidad."}, status=status.HTTP_400_BAD_REQUEST)
        
        comunidad.save()
        return Response({"mensaje": "La propiedad ha sido transferida exitosamente."}, status=status.HTTP_200_OK)


class MensajeComunidadViewSet(viewsets.ModelViewSet):
    serializer_class = MensajeComunidadSerializer
    authentication_classes = [AutenticacionJWT]
    pagination_class = PaginacionPublicaciones

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        if self.action == 'destroy':
            return [RequiereToken()]
        return [RequiereToken(), EsDueno()]

    def get_queryset(self):
        comunidad_id = self.request.query_params.get('comunidad')
        mensajes_activos = MensajeComunidad.objects.filter(activo=True).select_related('usuario', 'publicacion_reenviada').prefetch_related('archivos').order_by('-fecha_envio')

        if comunidad_id:
            return mensajes_activos.filter(comunidad_id=comunidad_id)
        return mensajes_activos

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        comunidad = serializer.validated_data['comunidad']
        es_miembro = UsuarioComunidad.objects.filter(usuario=request.user, comunidad=comunidad).exists()
        
        if not es_miembro:
            return Response(
                {"error": "Debes unirte a la comunidad para poder enviar mensajes."}, 
                status=status.HTTP_403_FORBIDDEN
            )
            
        serializer.save(usuario=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


    def destroy(self, request, *args, **kwargs):
        mensaje = self.get_object()

        es_autor = request.user.id == mensaje.usuario.id
        es_admin_comunidad = request.user.id == mensaje.comunidad.usuario.id
        
        if not es_autor and not es_admin_comunidad:
            return Response(
                {"error": "No tienes permiso para eliminar este mensaje. Solo el autor o el administrador pueden hacerlo."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        mensaje.activo = False
        mensaje.save()
        return Response(status=status.HTTP_204_NO_CONTENT)