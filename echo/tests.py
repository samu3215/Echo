from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from echo.models import Calificacion, Seguidor, Usuario
from echo.serializers.usuario_serializers import UsuarioDetalleSerializer
from echo.utils.notificaciones import construir_mensaje_resena, construir_mensaje_seguimiento
from echo.views.calificacion_views import CalificacionViewSet
from echo.views.usuario_views import RegistroUsuarioViewSet


class UsuarioPerfilResenasTests(TestCase):
    def setUp(self):
        self.empresa = Usuario.objects.create(
            email='empresa@test.com',
            nombre_usuario='empresa_demo',
            password='hashed-password',
            tipo_usuario='empresarial',
            nombre_negocio='Mi negocio',
            direccion='Calle 123',
            telefono='1234567890',
        )
        self.usuario_1 = Usuario.objects.create(
            email='cliente1@test.com',
            nombre_usuario='cliente_demo_1',
            password='hashed-password',
            tipo_usuario='normal',
            nombre='Cliente',
            apellido='Uno',
        )
        self.usuario_2 = Usuario.objects.create(
            email='cliente2@test.com',
            nombre_usuario='cliente_demo_2',
            password='hashed-password',
            tipo_usuario='normal',
            nombre='Cliente',
            apellido='Dos',
        )

        Calificacion.objects.create(
            usuario_califica=self.usuario_1,
            usuario_calificado=self.empresa,
            puntuacion=5,
            descripcion='Excelente servicio'
        )

        Calificacion.objects.create(
            usuario_califica=self.usuario_2,
            usuario_calificado=self.empresa,
            puntuacion=4,
            descripcion='Muy buena atención'
        )

    def test_serializer_incluye_resenas_en_el_perfil(self):
        data = UsuarioDetalleSerializer(self.empresa).data

        self.assertIn('resenas', data)
        self.assertEqual(len(data['resenas']), 2)
        self.assertEqual({item['puntuacion'] for item in data['resenas']}, {4, 5})

    def test_no_puede_crear_otra_resena_si_ya_califico(self):
        factory = APIRequestFactory()
        request = factory.post(
            '/api/calificaciones/',
            {
                'usuario_calificado': self.empresa.nombre_usuario,
                'puntuacion': 3,
                'descripcion': 'No debería permitirme crear otra reseña'
            },
            format='json',
        )
        force_authenticate(request, user=self.usuario_1)

        response = CalificacionViewSet.as_view({'post': 'create'})(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Calificacion.objects.filter(usuario_calificado=self.empresa, usuario_califica=self.usuario_1).count(), 1)

    def test_solo_el_autor_puede_actualizar_su_resena(self):
        calificacion = Calificacion.objects.get(usuario_califica=self.usuario_1, usuario_calificado=self.empresa)
        factory = APIRequestFactory()
        request = factory.patch(
            f'/api/calificaciones/{calificacion.id}/',
            {'puntuacion': 2, 'descripcion': 'Actualización no autorizada'},
            format='json',
        )
        force_authenticate(request, user=self.usuario_2)

        response = CalificacionViewSet.as_view({'patch': 'partial_update'})(request, pk=calificacion.id)

        self.assertEqual(response.status_code, 403)
        calificacion.refresh_from_db()
        self.assertEqual(calificacion.descripcion, 'Excelente servicio')

    def test_solo_el_autor_puede_eliminar_su_resena(self):
        calificacion = Calificacion.objects.get(usuario_califica=self.usuario_1, usuario_calificado=self.empresa)
        factory = APIRequestFactory()
        request = factory.delete(f'/api/calificaciones/{calificacion.id}/')
        force_authenticate(request, user=self.usuario_2)

        response = CalificacionViewSet.as_view({'delete': 'destroy'})(request, pk=calificacion.id)

        self.assertEqual(response.status_code, 403)
        self.assertTrue(Calificacion.objects.filter(pk=calificacion.pk).exists())

    def test_el_autor_puede_actualizar_su_resena(self):
        calificacion = Calificacion.objects.get(usuario_califica=self.usuario_1, usuario_calificado=self.empresa)
        factory = APIRequestFactory()
        request = factory.patch(
            f'/api/calificaciones/{calificacion.id}/',
            {'puntuacion': 3, 'descripcion': 'Reseña actualizada con éxito'},
            format='json',
        )
        force_authenticate(request, user=self.usuario_1)

        response = CalificacionViewSet.as_view({'patch': 'partial_update'})(request, pk=calificacion.id)

        self.assertEqual(response.status_code, 200)
        calificacion.refresh_from_db()
        self.assertEqual(calificacion.puntuacion, 3)
        self.assertEqual(calificacion.descripcion, 'Reseña actualizada con éxito')

    def test_serializer_incluye_datos_de_seguimiento(self):
        Seguidor.objects.create(seguidor=self.usuario_1, seguido=self.empresa)
        Seguidor.objects.create(seguidor=self.usuario_2, seguido=self.empresa)

        request = APIRequestFactory().get('/api/usuarios/empresa_demo/')
        request.user = self.usuario_1

        data = UsuarioDetalleSerializer(self.empresa, context={'request': request}).data

        self.assertEqual(data['seguidores_count'], 2)
        self.assertEqual(data['seguidos_count'], 0)
        self.assertTrue(data['esta_siguiendo'])

    def test_seguir_y_dejar_de_seguir_usuario(self):
        factory = APIRequestFactory()
        request = factory.post(f'/api/usuarios/{self.usuario_2.nombre_usuario}/seguir/')
        force_authenticate(request, user=self.usuario_1)

        response = RegistroUsuarioViewSet.as_view({'post': 'seguir'})(request, nombre_usuario=self.usuario_2.nombre_usuario)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Seguidor.objects.filter(seguidor=self.usuario_1, seguido=self.usuario_2).exists())
        self.assertTrue(response.data['esta_siguiendo'])
        self.assertEqual(response.data['seguidores_count'], 1)

        request_unfollow = factory.post(f'/api/usuarios/{self.usuario_2.nombre_usuario}/seguir/')
        force_authenticate(request_unfollow, user=self.usuario_1)

        response_unfollow = RegistroUsuarioViewSet.as_view({'post': 'seguir'})(request_unfollow, nombre_usuario=self.usuario_2.nombre_usuario)

        self.assertEqual(response_unfollow.status_code, 200)
        self.assertFalse(Seguidor.objects.filter(seguidor=self.usuario_1, seguido=self.usuario_2).exists())
        self.assertFalse(response_unfollow.data['esta_siguiendo'])
        self.assertEqual(response_unfollow.data['seguidores_count'], 0)

    def test_construye_mensaje_para_notificacion_de_resena(self):
        self.assertEqual(
            construir_mensaje_resena('cliente_demo_1'),
            'Tienes una reseña nueva de cliente_demo_1'
        )

    def test_construye_mensaje_para_notificacion_de_seguimiento(self):
        self.assertEqual(
            construir_mensaje_seguimiento('cliente_demo_1'),
            'cliente_demo_1 ha empezado a seguirte'
        )


