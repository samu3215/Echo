from rest_framework import viewsets, status
from rest_framework.response import Response
from ..models import Calificacion
from ..serializers.calificacion_serializers import CalificacionSerializer
from ..utils.autenticacion import AutenticacionJWT, RequiereToken, EsDueno

class CalificacionViewSet(viewsets.ModelViewSet):
    queryset = Calificacion.objects.all()
    serializer_class = CalificacionSerializer
    authentication_classes = [AutenticacionJWT]
    
    def get_permissions(self):
        if self.action in ['create']:
            return [RequiereToken()]
        if self.action in ['update', 'partial_update', 'destroy']:
            # Se asume que en EsDueno validas que obj.usuario_califica == request.user
            return [RequiereToken(), EsDueno()] 
        return [RequiereToken()]

    def perform_create(self, serializer):
        serializer.save(usuario_califica=self.request.user)