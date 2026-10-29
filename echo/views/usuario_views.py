from rest_framework import viewsets, status # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework.permissions import AllowAny # type: ignore
from rest_framework.decorators import action # type: ignore
from ..serializers.publicacion_serializers import NotificacionSerializer
from echo.models import *
from echo.serializers.usuario_serializers import *
from echo.utils.autenticacion import *
from echo.utils.tokens import *
from rest_framework.views import APIView
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.hashers import make_password, check_password
import secrets

class RegistroUsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.filter(activo=True)
    serializer_class = RegistroUsuarioSerializer
    lookup_field = 'nombre_usuario'

    authentication_classes = [AutenticacionJWT]

    def get_permissions(self):
       
        if self.action in ['create', 'list', 'retrieve', 'listar_seguidores', 'listar_seguidos']:
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

    @action(detail=True, methods=['get'], url_path='seguidores')
    def listar_seguidores(self, request, nombre_usuario=None):
        usuario = self.get_object()
        seguidores = Seguidor.objects.filter(seguido=usuario).select_related('seguidor')
        usuarios_seguidores = [seg.seguidor for seg in seguidores]
        serializer = RegistroUsuarioSerializer(usuarios_seguidores, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    @action(detail=True, methods=['get'], url_path='seguidos')
    def listar_seguidos(self, request, nombre_usuario=None):
        usuario = self.get_object()
        seguidos = Seguidor.objects.filter(seguidor=usuario).select_related('seguido')
        usuarios_seguidos = [seg.seguido for seg in seguidos]
        serializer = RegistroUsuarioSerializer(usuarios_seguidos, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

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
        usuario.calificaciones_dadas.update(activo=False)
        
        return Response(
            {"mensaje": "Usuario eliminado correctamente."}, 
            status=status.HTTP_200_OK
        )

class EnviarCodigoRegistroAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        if not email:
            return Response({"error": "Correo requerido"}, status=status.HTTP_400_BAD_REQUEST)
        
        codigo = f'{secrets.randbelow(1000000):06d}'
        expiracion = timezone.now() + timedelta(minutes=5)
        
        VerificacionRegistro.objects.update_or_create(
            email=email,
            defaults={'codigo_hash': make_password(codigo), 'expira_en': expiracion}
        )
        
        send_mail(
            'Verifica tu correo en Echo',
            f'Tu código de verificación para registrarte es: {codigo}\nEste código vence en 5 minutos.',
            settings.DEFAULT_FROM_EMAIL,
            [email],
            fail_silently=False,
        )
        return Response({"mensaje": "Código enviado"}, status=status.HTTP_200_OK)


class VerificarCodigoRegistroAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        codigo = request.data.get('codigo')
        
        try:
            verificacion = VerificacionRegistro.objects.get(email=email)
        except VerificacionRegistro.DoesNotExist:
            return Response({"error": "No hay código pendiente para este correo."}, status=status.HTTP_400_BAD_REQUEST)
            
        if timezone.now() > verificacion.expira_en or not check_password(codigo, verificacion.codigo_hash):
            return Response({"error": "Código inválido o expirado."}, status=status.HTTP_400_BAD_REQUEST)
            
        verificacion.delete() # Se borra porque ya fue verificado exitosamente
        return Response({"mensaje": "Correo verificado"}, status=status.HTTP_200_OK)