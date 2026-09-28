from rest_framework import viewsets # type: ignore
from  ..models import *


class CrearPublicacionViewSet(viewsets.ModelViewSet):
    queryset = Publicacion.objects()