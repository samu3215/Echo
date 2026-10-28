from rest_framework import viewsets, status # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework.permissions import AllowAny # type: ignore
from rest_framework.decorators import action # type: ignore
from ..serializers.publicacion_serializers import NotificacionSerializer
from echo.models import *
from echo.serializers.usuario_serializers import *
from echo.utils.autenticacion import *
from echo.utils.tokens import *

class RegistroUsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.filter(activo=True)
    serializer_class = RegistroUsuarioSerializer
    lookup_field = 'nombre_usuario'

    authentication_classes = [AutenticacionJWT]

    def get_permissions(self):
       
        if self.action in ['create', 'list', 'retrieve']:
            return [AllowAny()]
        
        if self.action in ['seguir_usuario', 'notificaciones']:
            return [RequiereToken()]
        
        return [RequiereToken(), EsDueno()]

    @action(detail=False, methods=['get'], url_path='notificaciones')
    def notificaciones(self, request):
        if not hasattr(request.user, 'id'):
            return Response({"error": "No autorizado"}, status=status.HTTP_401_UNAUTHORIZED)
            
        notifs_mostrar = Notificacion.objects.filter(usuario_destino=request.user).select_related('usuario_origen').order_by('-fecha_creacion')[:15]
        
        serializer = NotificacionSerializer(notifs_mostrar, many=True)
        no_leidas = Notificacion.objects.filter(usuario_destino=request.user, leido=False).count()
        
        todas_notifs = Notificacion.objects.filter(usuario_destino=request.user).order_by('-fecha_creacion')
        if todas_notifs.count() > 50:
            ids_a_conservar = list(todas_notifs.values_list('id', flat=True)[:50])
            Notificacion.objects.filter(usuario_destino=request.user).exclude(id__in=ids_a_conservar).delete()

        return Response({
            "sin_leer": no_leidas, 
            "lista": serializer.data
        }, status=status.HTTP_200_OK)

    @action(detail=False, methods=['post'], url_path='marcar-notificaciones')
    def marcar_notificaciones(self, request):
        Notificacion.objects.filter(usuario_destino=request.user, leido=False).update(leido=True)
        return Response({"mensaje": "Notificaciones leídas"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'], url_path='seguir')
    def seguir_usuario(self, request, nombre_usuario=None):
        if not hasattr(request.user, 'id'):
            return Response({"error": "Debes iniciar sesión"}, status=status.HTTP_401_UNAUTHORIZED)

        usuario_a_seguir = self.get_object()
        usuario_actual = request.user

        if usuario_actual == usuario_a_seguir:
            return Response({"error": "No puedes seguirte a ti mismo."}, status=status.HTTP_400_BAD_REQUEST)

        seguimiento = Seguidor.objects.filter(seguidor=usuario_actual, seguido=usuario_a_seguir).first()
        
        if seguimiento:
            seguimiento.delete()
            Notificacion.objects.create(
                usuario_destino=usuario_a_seguir, 
                usuario_origen=usuario_actual, 
                tipo='dejar_seguir'
            )
            return Response({"siguiendo": False}, status=status.HTTP_200_OK)
        else:
            Seguidor.objects.create(seguidor=usuario_actual, seguido=usuario_a_seguir)
            Notificacion.objects.create(
                usuario_destino=usuario_a_seguir, 
                usuario_origen=usuario_actual, 
                tipo='seguir'
            )
            return Response({"siguiendo": True}, status=status.HTTP_201_CREATED)

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

    def update(self, request, *args, **kwargs):
        instance = self.get_object()

        serializer = self.get_serializer(instance, data=request.data, partial=kwargs.pop('partial', False))
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer) 

        nuevo_token = generar_token_jwt(instance)

        return Response({
            "mensaje": "Perfil actualizado con éxito",
            "datos": serializer.data,
            "token": nuevo_token
        }, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):

        usuario = self.get_object()
        usuario.activo = False
        usuario.save()

        usuario.publicaciones.update(activo=False)
        usuario.comentarios.update(activo=False)
        usuario.comunidades_creadas.update(activo=False)
        usuario.mensajes_comunidad.update(activo=False)
        
        return Response(
            {"mensaje": "Usuario eliminado correctamente."}, 
            status=status.HTTP_200_OK
        )

