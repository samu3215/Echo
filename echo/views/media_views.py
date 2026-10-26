from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from echo.utils.cloudinary import subir_archivo_cloudinary

class UploadMediaAPIView(APIView):
    def post(self, request):
        archivo = request.FILES.get('archivo')
        
        carpeta = request.data.get('carpeta', 'general')

        if not archivo:
            return Response({"error": "No se envió ningún archivo."}, status=status.HTTP_400_BAD_REQUEST)

        
        es_perfil = carpeta == 'perfiles'

        url_segura = subir_archivo_cloudinary(archivo, carpeta, es_perfil)

        return Response({
            "mensaje": "Archivo subido exitosamente",
            "url": url_segura
        }, status=status.HTTP_201_CREATED)