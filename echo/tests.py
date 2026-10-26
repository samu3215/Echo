import re

from django.contrib.auth.hashers import check_password, make_password
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from echo.models import RecuperacionContrasena, Usuario
from echo.serializers.usuario_serializers import RegistroUsuarioSerializer


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