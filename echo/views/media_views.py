from rest_framework.views import APIView #type: ignore
from rest_framework.response import Response #type: ignore
from rest_framework import status #type: ignore
from echo.utils.cloudinary import *

class UploadMediaAPIView(APIView):
    def post(self, request):
        archivo = request.FILES.get('archivo')
        
        carpeta = request.data.get('carpeta', 'general')

        if not archivo:
            return Response({"error": "No se envió ningún archivo."}, status=status.HTTP_400_BAD_REQUEST)

        
        es_perfil = True if carpeta == 'perfiles' else False

        url_segura = subir_archivo_cloudinary(archivo, carpeta, es_perfil)

        return Response({
            "mensaje": "Archivo subido exitosamente",
            "url": url_segura
        }, status=status.HTTP_201_CREATED)