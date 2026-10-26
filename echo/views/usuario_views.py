from rest_framework import viewsets, status # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework.permissions import AllowAny # type: ignore
from rest_framework.decorators import action # type: ignore

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
            
        datos = []
        
        def get_foto_url(usuario):
            if usuario.foto_perfil and hasattr(usuario.foto_perfil, 'url'):
                return request.build_absolute_uri(usuario.foto_perfil.url) if request else usuario.foto_perfil.url
            return None

        seguidores = Seguidor.objects.filter(seguido=request.user).select_related('seguidor')
        for seg in seguidores:
            datos.append({
                "id": f"seg_{seg.id}",
                "tipo": "seguidor",
                "usuario_origen": seg.seguidor.nombre_usuario,
                "foto_perfil": get_foto_url(seg.seguidor),
                "fecha": seg.fecha_seguimiento.isoformat() if seg.fecha_seguimiento else None
            })
            
        calificaciones = Calificacion.objects.filter(usuario_calificado=request.user).select_related('usuario_califica')
        for cal in calificaciones:
            datos.append({
                "id": f"cal_{cal.id}",
                "tipo": "calificacion",
                "usuario_origen": cal.usuario_califica.nombre_usuario,
                "foto_perfil": get_foto_url(cal.usuario_califica),
                "puntuacion": cal.puntuacion,
                "fecha": cal.fecha_creacion.isoformat() if cal.fecha_creacion else None
            })
            
        datos.sort(key=lambda x: x['fecha'] or '', reverse=True)
        
        return Response(datos[:50], status=status.HTTP_200_OK)

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
            return Response({"siguiendo": False}, status=status.HTTP_200_OK)
        else:
            Seguidor.objects.create(seguidor=usuario_actual, seguido=usuario_a_seguir)
            return Response({"siguiendo": True}, status=status.HTTP_201_CREATED)
