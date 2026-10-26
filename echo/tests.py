import re

from django.contrib.auth.hashers import check_password, make_password
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from echo.models import Publicacion, RecuperacionContrasena, Seguidor, Usuario
from echo.serializers.usuario_serializers import RegistroUsuarioSerializer
from echo.utils.tokens import generar_token_jwt


@override_settings(EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend')
class RecuperacionContrasenaTests(TestCase):
    def setUp(self):
        self.usuario = Usuario.objects.create(
            email='usuario@correo.com',
            nombre_usuario='usuario',
            password=make_password('ContrasenaAnterior123!'),
            tipo_usuario='normal',
        )
        self.client = APIClient()

    def test_flujo_completo_y_token_de_un_solo_uso(self):
        solicitud = self.client.post(
            '/api/recuperacion/solicitar-codigo/',
            {'email': self.usuario.email},
            format='json',
        )
        self.assertEqual(solicitud.status_code, 200)
        self.assertEqual(
            solicitud.data,
            {
                'mensaje': 'Código enviado con éxito',
                'expira_en': 3,
                'expires_at': 3,
                'tiempo_expiracion': 3,
                'exp': 3,
            },
        )
        recuperacion = self.usuario.recuperacion_contrasena
        segundos_restantes = (recuperacion.codigo_expira_en - timezone.now()).total_seconds()
        self.assertAlmostEqual(segundos_restantes, 180, delta=1)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].from_email, 'echobussines4@gmail.com')
        self.assertIn('3 minutos', mail.outbox[0].body)

        codigo = re.search(r'\b(\d{6})\b', mail.outbox[0].body).group(1)
        self.assertTrue(mail.outbox[0].alternatives)
        self.assertIn(codigo, mail.outbox[0].alternatives[0][0])
        verificacion = self.client.post(
            '/api/recuperacion/verificar-codigo/',
            {'email': self.usuario.email, 'codigo': codigo},
            format='json',
        )
        self.assertEqual(verificacion.status_code, 200)
        token = verificacion.data['token']
        self.assertEqual(
            verificacion.data,
            {
                'mensaje': 'Código verificado correctamente',
                'token': token,
                'access_token': token,
                'temp_token': token,
            },
        )

        restablecimiento = self.client.post(
            '/api/recuperacion/restablecer-contrasena/',
            {
                'password': 'ContrasenaNueva456!',
                'confirmar_password': 'ContrasenaNueva456!',
            },
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(restablecimiento.status_code, 200)
        self.assertEqual(
            restablecimiento.data,
            {'mensaje': 'La contraseña se restableció correctamente.'},
        )

        self.usuario.refresh_from_db()
        self.assertTrue(check_password('ContrasenaNueva456!', self.usuario.password))
        self.assertFalse(
            RecuperacionContrasena.objects.filter(usuario=self.usuario).exists()
        )
        reutilizacion = self.client.post(
            '/api/recuperacion/restablecer-contrasena/',
            {
                'password': 'OtraContrasena789!',
                'confirmar_password': 'OtraContrasena789!',
            },
            format='json',
            HTTP_AUTHORIZATION=f'Bearer {token}',
        )
        self.assertEqual(reutilizacion.status_code, 401)

    def test_codigo_incorrecto_no_emite_token(self):
        self.client.post(
            '/api/recuperacion/solicitar-codigo/',
            {'email': self.usuario.email},
            format='json',
        )

        codigo_valido = re.search(r'\b(\d{6})\b', mail.outbox[0].body).group(1)
        codigo_invalido = '000000' if codigo_valido != '000000' else '000001'
        respuesta = self.client.post(
            '/api/recuperacion/verificar-codigo/',
            {'email': self.usuario.email, 'codigo': codigo_invalido},
            format='json',
        )
        self.assertEqual(respuesta.status_code, 400)

    def test_codigo_se_invalida_despues_de_verificar(self):
        self.client.post(
            '/api/recuperacion/solicitar-codigo/',
            {'email': self.usuario.email},
            format='json',
        )
        codigo = re.search(r'\b(\d{6})\b', mail.outbox[0].body).group(1)

        primera_verificacion = self.client.post(
            '/api/recuperacion/verificar-codigo/',
            {'email': self.usuario.email, 'codigo': codigo},
            format='json',
        )
        self.assertEqual(primera_verificacion.status_code, 200)

        segunda_verificacion = self.client.post(
            '/api/recuperacion/verificar-codigo/',
            {'email': self.usuario.email, 'codigo': codigo},
            format='json',
        )
        self.assertEqual(segunda_verificacion.status_code, 400)

    def test_restaurar_acepta_token_y_passwords_del_cuerpo(self):
        self.client.post(
            '/api/recuperacion/solicitar-codigo/',
            {'email': self.usuario.email},
            format='json',
        )
        codigo = re.search(r'\b(\d{6})\b', mail.outbox[0].body).group(1)
        verificacion = self.client.post(
            '/api/recuperacion/verificar-codigo/',
            {'email': self.usuario.email, 'codigo': codigo},
            format='json',
        )
        token = verificacion.data['token']

        respuesta = self.client.post(
            '/api/recuperacion/restablecer-contrasena/',
            {
                'token': token,
                'password': 'OtraContrasenaSegura789!',
                'confirmar_password': 'OtraContrasenaSegura789!',
            },
            format='json',
        )
        self.assertEqual(respuesta.status_code, 200)
        self.usuario.refresh_from_db()
        self.assertTrue(check_password('OtraContrasenaSegura789!', self.usuario.password))
        self.assertFalse(
            RecuperacionContrasena.objects.filter(usuario=self.usuario).exists()
        )

    def test_restaurar_rechaza_confirmacion_distinta(self):
        respuesta = self.client.post(
            '/api/recuperacion/restablecer-contrasena/',
            {
                'token': 'token-solo-para-validacion',
                'password': 'UnaContrasenaSegura789!',
                'confirmar_password': 'OtraContrasenaSegura789!',
            },
            format='json',
        )
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn('confirmar_password', respuesta.data)

    def test_correo_no_registrado_retorna_error(self):
        respuesta = self.client.post(
            '/api/recuperacion/solicitar-codigo/',
            {'email': 'desconocido@correo.com'},
            format='json',
        )
        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(len(mail.outbox), 0)


class RegistroSinActivacionTests(TestCase):
    def test_registro_activa_la_cuenta_y_permite_login_inmediato(self):
        client = APIClient()
        password = 'UnaClaveCompleja923!'
        registro = client.post(
            '/api/usuarios/',
            {
                'email': 'nueva@correo.com',
                'nombre_usuario': 'nueva',
                'password': password,
                'confirmar_password': password,
                'tipo_usuario': 'normal',
                'nombre': 'Nueva',
                'apellido': 'Cuenta',
            },
            format='json',
        )

        self.assertEqual(registro.status_code, 201)
        usuario = Usuario.objects.get(email='nueva@correo.com')
        self.assertTrue(usuario.activo)
        self.assertNotEqual(usuario.password, password)
        self.assertTrue(usuario.password.startswith('pbkdf2_sha256$'))
        self.assertTrue(usuario.check_password(password))
        self.assertEqual(len(mail.outbox), 0)

        login = client.post(
            '/api/login/',
            {'identificador': usuario.nombre_usuario, 'password': password},
            format='json',
        )
        self.assertEqual(login.status_code, 200)

    def test_actualizar_contrasena_guarda_hash_y_valida_password(self):
        usuario = Usuario.objects.create(
            email='perfil@correo.com',
            nombre_usuario='perfil',
            password=make_password('ContrasenaAnterior123!'),
            tipo_usuario='normal',
            nombre='Perfil',
            apellido='Prueba',
        )
        nueva_password = 'ContrasenaNueva456!'
        serializer = RegistroUsuarioSerializer(
            usuario,
            {
                'password': nueva_password,
                'confirmar_password': nueva_password,
            },
            partial=True,
        )
        self.assertTrue(serializer.is_valid(), serializer.errors)
        serializer.save()

        usuario.refresh_from_db()
        self.assertNotEqual(usuario.password, nueva_password)
        self.assertTrue(usuario.password.startswith('pbkdf2_sha256$'))
        self.assertTrue(usuario.check_password(nueva_password))


class PublicacionViewSetTests(TestCase):
    def setUp(self):
        self.autor = Usuario.objects.create(
            email='autor@correo.com',
            nombre_usuario='autor',
            password=make_password('ContrasenaAutor123!'),
            tipo_usuario='normal',
            nombre='Autor',
            apellido='Prueba',
        )
        self.otro_usuario = Usuario.objects.create(
            email='otro@correo.com',
            nombre_usuario='otro',
            password=make_password('ContrasenaOtro123!'),
            tipo_usuario='normal',
            nombre='Otro',
            apellido='Usuario',
        )
        self.client = APIClient()
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {generar_token_jwt(self.autor)}'
        )

    def test_usuario_autenticado_crea_publicacion_y_comentario(self):
        respuesta_publicacion = self.client.post(
            '/api/publicaciones/',
            {'contenido': '<p>Publicación de prueba</p>', 'tipo_media': 'texto'},
            format='json',
        )
        self.assertEqual(respuesta_publicacion.status_code, 201)
        datos_publicacion = respuesta_publicacion.data['datos']
        self.assertEqual(datos_publicacion['contenido'], 'Publicación de prueba')
        self.assertEqual(datos_publicacion['usuario']['id'], self.autor.id)

        respuesta_comentario = self.client.post(
            '/api/comentarios/',
            {
                'contenido': '<p>Comentario de prueba</p>',
                'publicacion': datos_publicacion['id'],
            },
            format='json',
        )
        self.assertEqual(respuesta_comentario.status_code, 201)
        self.assertEqual(respuesta_comentario.data['contenido'], 'Comentario de prueba')
        self.assertEqual(respuesta_comentario.data['usuario']['id'], self.autor.id)

    def test_solo_el_propietario_puede_modificar_publicacion(self):
        publicacion = Publicacion.objects.create(
            usuario=self.autor,
            contenido='Original',
            tipo_media='texto',
        )
        self.client.credentials(
            HTTP_AUTHORIZATION=f'Bearer {generar_token_jwt(self.otro_usuario)}'
        )

        respuesta = self.client.patch(
            f'/api/publicaciones/{publicacion.id}/',
            {'contenido': 'Modificación no autorizada'},
            format='json',
        )

        self.assertEqual(respuesta.status_code, 403)

    def test_feed_perfil_likes_y_paginacion(self):
        Publicacion.objects.create(
            usuario=self.autor,
            contenido='Publicación del autor',
            tipo_media='texto',
        )
        Publicacion.objects.create(
            usuario=self.otro_usuario,
            contenido='Publicación del otro usuario',
            tipo_media='texto',
        )
        self.client.credentials()

        respuesta_feed = self.client.get('/api/publicaciones/?tamano=1')
        self.assertEqual(respuesta_feed.status_code, 200)
        self.assertEqual(respuesta_feed.data['count'], 2)
        self.assertEqual(len(respuesta_feed.data['results']), 1)

        respuesta_perfil = self.client.get('/api/publicaciones/?usuario=autor')
        self.assertEqual(respuesta_perfil.status_code, 200)
        self.assertEqual(respuesta_perfil.data['count'], 1)
        self.assertEqual(
            respuesta_perfil.data['results'][0]['usuario']['nombre_usuario'],
            'autor',
        )

        publicacion = Publicacion.objects.get(usuario=self.otro_usuario)
        publicacion.likes_publicacion.create(usuario=self.autor)
        respuesta_likes = self.client.get('/api/publicaciones/?like=autor')
        self.assertEqual(respuesta_likes.status_code, 200)
        self.assertEqual(respuesta_likes.data['count'], 1)
        self.assertEqual(respuesta_likes.data['results'][0]['id'], publicacion.id)

    def test_like_se_alterna_y_rechaza_like_a_publicacion_propia(self):
        publicacion_otro = Publicacion.objects.create(
            usuario=self.otro_usuario,
            contenido='Publicación para dar like',
            tipo_media='texto',
        )
        respuesta_like = self.client.post(
            f'/api/publicaciones/{publicacion_otro.id}/like/',
        )
        self.assertEqual(respuesta_like.status_code, 204)
        self.assertTrue(
            publicacion_otro.likes_publicacion.filter(usuario=self.autor).exists()
        )

        respuesta_quitar_like = self.client.post(
            f'/api/publicaciones/{publicacion_otro.id}/like/',
        )
        self.assertEqual(respuesta_quitar_like.status_code, 204)
        self.assertFalse(
            publicacion_otro.likes_publicacion.filter(usuario=self.autor).exists()
        )

        publicacion_propia = Publicacion.objects.create(
            usuario=self.autor,
            contenido='Publicación propia',
            tipo_media='texto',
        )
        respuesta_propia = self.client.post(
            f'/api/publicaciones/{publicacion_propia.id}/like/',
        )
        self.assertEqual(respuesta_propia.status_code, 403)

    def test_feed_autenticado_prioriza_publicaciones_de_seguidos(self):
        Seguidor.objects.create(
            seguidor=self.autor,
            seguido=self.otro_usuario,
        )
        Publicacion.objects.create(
            usuario=self.autor,
            contenido='Publicación propia',
            tipo_media='texto',
        )
        publicacion_seguido = Publicacion.objects.create(
            usuario=self.otro_usuario,
            contenido='Publicación de seguido',
            tipo_media='texto',
        )

        respuesta = self.client.get('/api/publicaciones/')

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.data['count'], 1)
        self.assertEqual(respuesta.data['results'][0]['id'], publicacion_seguido.id)