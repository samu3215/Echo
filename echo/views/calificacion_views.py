from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.response import Response
from echo.models import Calificacion, Usuario
from echo.utils.autenticacion import AutenticacionJWT, RequiereToken


class CalificacionViewSet(viewsets.ViewSet):
    authentication_classes = [AutenticacionJWT]
    permission_classes = [RequiereToken]

    def get_calificacion(self, pk):
        return get_object_or_404(Calificacion, pk=pk)

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

    def _actualizar_calificacion(self, request, calificacion):
        if request.user != calificacion.usuario_califica:
            return Response({'error': 'No tienes permiso para editar esta reseña.'}, status=status.HTTP_403_FORBIDDEN)

        puntuacion = request.data.get('puntuacion', calificacion.puntuacion)
        descripcion = request.data.get('descripcion', calificacion.descripcion)

        try:
            puntuacion = int(puntuacion)
        except (TypeError, ValueError):
            return Response({'error': 'La puntuación debe ser un número entre 1 y 5.'}, status=status.HTTP_400_BAD_REQUEST)

        if puntuacion < 1 or puntuacion > 5:
            return Response({'error': 'La puntuación debe estar entre 1 y 5.'}, status=status.HTTP_400_BAD_REQUEST)

        calificacion.puntuacion = puntuacion
        calificacion.descripcion = descripcion
        calificacion.save()

        return Response({
            'mensaje': 'Calificación actualizada con éxito',
            'calificacion': {
                'id': calificacion.id,
                'puntuacion': calificacion.puntuacion,
                'descripcion': calificacion.descripcion,
            }
        }, status=status.HTTP_200_OK)

    def update(self, request, pk=None):
        calificacion = self.get_calificacion(pk)
        return self._actualizar_calificacion(request, calificacion)

    def partial_update(self, request, pk=None):
        calificacion = self.get_calificacion(pk)
        return self._actualizar_calificacion(request, calificacion)

    def destroy(self, request, pk=None):
        calificacion = self.get_calificacion(pk)

        if request.user != calificacion.usuario_califica:
            return Response({'error': 'No tienes permiso para eliminar esta reseña.'}, status=status.HTTP_403_FORBIDDEN)

        calificacion.delete()
        return Response({'mensaje': 'Calificación eliminada con éxito'}, status=status.HTTP_200_OK)