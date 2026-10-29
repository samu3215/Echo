from rest_framework import viewsets, status
from rest_framework.response import Response
from ..models import Calificacion
from ..serializers.calificacion_serializers import CalificacionSerializer
from ..utils.autenticacion import *

class CalificacionViewSet(viewsets.ModelViewSet):

    serializer_class = CalificacionSerializer
    authentication_classes = [AutenticacionJWT]

    def get_queryset(self):
        return Calificacion.objects.filter(activo=True, usuario_califica__activo=True)

    def get_permissions(self):
        if self.action in ['create']:
            return [RequiereToken()]
        if self.action in ['update', 'partial_update', 'destroy']:
            return [RequiereToken(), EsDueno()] 
        return [RequiereToken()]

    def perform_create(self, serializer):
        calificacion = serializer.save(usuario_califica=self.request.user)
        
        # Validamos explícitamente que el destino sea empresarial para notificar
        if calificacion.usuario_calificado.tipo_usuario == 'empresarial':
            Notificacion.objects.create(
                usuario_destino=calificacion.usuario_calificado,
                usuario_origen=self.request.user,
                tipo='calificacion',
                puntuacion=calificacion.puntuacion
            )

    def destroy(self, request, *args, **kwargs):
        calificacion = self.get_object()
        calificacion.activo = False 
        calificacion.save()
        return Response(status=status.HTTP_204_NO_CONTENT)