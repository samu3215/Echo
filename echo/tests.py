from django.test import TestCase
from rest_framework.test import APIRequestFactory, force_authenticate

from echo.models import Calificacion, Usuario
from echo.serializers.usuario_serializers import UsuarioDetalleSerializer
from echo.views.calificacion_views import CalificacionViewSet


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


