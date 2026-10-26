from rest_framework import viewsets

from echo.models import Publicacion


class CrearPublicacionViewSet(viewsets.ModelViewSet):
    queryset = Publicacion.objects()