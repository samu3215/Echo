from rest_framework import viewsets, status
from rest_framework.response import Response
from echo.models import Calificacion, Usuario
from echo.utils.autenticacion import AutenticacionJWT, RequiereToken


class CalificacionViewSet(viewsets.ViewSet):
    authentication_classes = [AutenticacionJWT]
    permission_classes = [RequiereToken]

    def create(self, request):
        usuario_califica = request.user
        nombre_usuario_calificado = request.data.get('usuario_calificado')
        puntuacion = request.data.get('puntuacion')
        descripcion = request.data.get('descripcion', '')

        try:
            usuario_calificado = Usuario.objects.get(nombre_usuario=nombre_usuario_calificado)
        except Usuario.DoesNotExist:
            return Response({'error': 'El usuario a calificar no existe'}, status=status.HTTP_404_NOT_FOUND)

        if usuario_califica == usuario_calificado:
            return Response({'error': 'No puedes calificarte a ti mismo'}, status=status.HTTP_400_BAD_REQUEST)

        if Calificacion.objects.filter(usuario_califica=usuario_califica, usuario_calificado=usuario_calificado).exists():
            return Response({'error': 'Ya dejaste una reseña para esta empresa. No puedes crear otra.'}, status=status.HTTP_400_BAD_REQUEST)

        Calificacion.objects.create(
            puntuacion=puntuacion,
            descripcion=descripcion,
            usuario_califica=usuario_califica,
            usuario_calificado=usuario_calificado
        )
        
        return Response({'mensaje': 'Calificación guardada con éxito'}, status=status.HTTP_201_CREATED)