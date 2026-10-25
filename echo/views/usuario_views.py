# from rest_framework import viewsets, status # type: ignore
# from rest_framework.response import Response # type: ignore
# from rest_framework.permissions import AllowAny # type: ignore

# from echo.models import *
# from echo.serializers.usuario_serializers import *
# from echo.utils.autenticacion import *
# from echo.utils.tokens import *


# from rest_framework.decorators import api_view, permission_classes
# from rest_framework.permissions import IsAuthenticated
# from ..models import Perfil


# @api_view(['PUT', 'PATCH'])
# @permission_classes([IsAuthenticated])
# def actualizar_configuracion(request):
#     user = request.user
#     perfil, _ = Perfil.objects.get_or_create(usuario=user)

#     # Actualizar datos de User
#     if 'email' in request.data:
#         user.email = request.data['email']
#         user.save()

#     # Actualizar datos de Perfil
#     perfil.nombre_completo = request.data.get('nombre_completo', perfil.nombre_completo)
#     perfil.biografia = request.data.get('biografia', perfil.biografia)
#     perfil.sitio_web = request.data.get('sitio_web', perfil.sitio_web)
#     perfil.privado = request.data.get('privado', perfil.privado)
    
#     if 'avatar' in request.FILES:
#         perfil.avatar = request.FILES['avatar']

#     perfil.save()

#     return Response({
#         "mensaje": "Configuración actualizada correctamente",
#         "usuario": {
#             "username": user.username,
#             "email": user.email,
#             "nombre_completo": perfil.nombre_completo,
#             "biografia": perfil.biografia,
#             "sitio_web": perfil.sitio_web,
#             "privado": perfil.privado
#         }
#     }, status=status.HTTP_200_OK)





























# class RegistroUsuarioViewSet(viewsets.ModelViewSet):
#     queryset = Usuario.objects.filter(activo=True)
#     serializer_class = RegistroUsuarioSerializer
#     lookup_field = 'nombre_usuario'

#     authentication_classes = [AutenticacionJWT]

#     def get_permissions(self):
       
#         if self.action in ['create', 'list', 'retrieve']:
#             return [AllowAny()]
        
#         return [RequiereToken(), EsDuenoDelPerfil()]

#     def create(self, request, *args, **kwargs):
#         serializer = self.get_serializer(data=request.data)
#         serializer.is_valid(raise_exception=True)
#         self.perform_create(serializer)
        
#         return Response(
#             {
#                 "mensaje": "Usuario registrado exitosamente",
#                 "datos": serializer.data
#             }, 
#             status=status.HTTP_201_CREATED
#         )

#     def update(self, request, *args, **kwargs):
#         instance = self.get_object()

#         serializer = self.get_serializer(instance, data=request.data, partial=kwargs.pop('partial', False))
#         serializer.is_valid(raise_exception=True)
#         self.perform_update(serializer) 

#         nuevo_token = generar_token_jwt(instance)

#         return Response({
#             "mensaje": "Perfil actualizado con éxito",
#             "datos": serializer.data,
#             "token": nuevo_token
#         }, status=status.HTTP_200_OK)

#     def destroy(self, request, *args, **kwargs):

#         usuario = self.get_object()
#         usuario.activo = False
#         usuario.save()
        
#         return Response(
#             {"mensaje": "Usuario eliminado correctamente."}, 
#             status=status.HTTP_200_OK
#         )



from rest_framework import viewsets, status # type: ignore
from rest_framework.response import Response # type: ignore
from rest_framework.permissions import AllowAny # type: ignore
from rest_framework.decorators import api_view, authentication_classes, permission_classes # type: ignore

from echo.models import Usuario
from echo.serializers.usuario_serializers import RegistroUsuarioSerializer
from echo.utils.autenticacion import AutenticacionJWT, RequiereToken, EsDuenoDelPerfil
from echo.utils.tokens import generar_token_jwt


@api_view(['PUT', 'PATCH'])
@authentication_classes([AutenticacionJWT])
@permission_classes([RequiereToken])
def actualizar_configuracion(request):
    usuario = request.usuario_logueado  # O request.user según cómo extraiga el token tu AutenticacionJWT

    if not usuario:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)

    # Actualizar campos dinámicamente si vienen en la petición
    if 'email' in request.data:
        usuario.email = request.data['email']
        
    if 'descripcion' in request.data:
        usuario.descripcion = request.data['descripcion']

    if 'nombre' in request.data:
        usuario.nombre = request.data['nombre']

    if 'apellido' in request.data:
        usuario.apellido = request.data['apellido']

    if 'foto_perfil' in request.FILES:
        usuario.foto_perfil = request.FILES['foto_perfil']

    usuario.save()

    return Response({
        "mensaje": "Configuración actualizada correctamente",
        "usuario": {
            "nombre_usuario": usuario.nombre_usuario,
            "email": usuario.email,
            "nombre": getattr(usuario, 'nombre', ''),
            "apellido": getattr(usuario, 'apellido', ''),
            "descripcion": getattr(usuario, 'descripcion', ''),
            "foto_perfil": usuario.foto_perfil.url if usuario.foto_perfil else None
        }
    }, status=status.HTTP_200_OK)


class RegistroUsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuario.objects.filter(activo=True)
    serializer_class = RegistroUsuarioSerializer
    lookup_field = 'nombre_usuario'

    authentication_classes = [AutenticacionJWT]

    def get_permissions(self):
        if self.action in ['create', 'list', 'retrieve']:
            return [AllowAny()]
        
        return [RequiereToken(), EsDuenoDelPerfil()]

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
        
        return Response(
            {"mensaje": "Usuario eliminado correctamente."}, 
            status=status.HTTP_200_OK
        )








@api_view(['GET'])
@authentication_classes([AutenticacionJWT])
@permission_classes([RequiereToken])
def obtener_perfil(request):
    # Extraer el usuario autenticado cargado por tu middleware personalizado
    usuario = getattr(request, 'usuario_logueado', getattr(request, 'user', None))

    if not usuario or not usuario.is_authenticated if hasattr(usuario, 'is_authenticated') else not usuario:
        return Response({"error": "No autenticado"}, status=status.HTTP_401_UNAUTHORIZED)

    serializer = RegistroUsuarioSerializer(usuario)
    return Response(serializer.data, status=status.HTTP_200_OK)