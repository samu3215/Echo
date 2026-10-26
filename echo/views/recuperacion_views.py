import logging
import secrets
import smtplib
import uuid
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.password_validation import validate_password
from django.core import signing
from django.core.exceptions import ValidationError
from django.core.mail import BadHeaderError, send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from echo.models import RecuperacionContrasena, Usuario


logger = logging.getLogger(__name__)

CODIGO_EXPIRACION = timedelta(minutes=3)
TOKEN_EXPIRACION = timedelta(minutes=3)
TOKEN_SALT = 'echo.recuperacion-contrasena'


class SolicitarCodigoSerializer(serializers.Serializer):
    email = serializers.EmailField()


class VerificarCodigoSerializer(serializers.Serializer):
    email = serializers.EmailField()
    codigo = serializers.RegexField(regex=r'^\d{6}$')


class RestablecerContrasenaSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, required=True, allow_blank=False)
    confirmar_password = serializers.CharField(write_only=True, required=True, allow_blank=False)
    token = serializers.CharField(write_only=True, required=True, allow_blank=False)

    def validate(self, attrs):
        if attrs['password'] != attrs['confirmar_password']:
            raise serializers.ValidationError(
                {'confirmar_password': 'Los campos de contraseña no coinciden.'}
            )
        return attrs


class RecuperacionAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]


class SolicitarCodigoAPIView(RecuperacionAPIView):
    def post(self, request):
        serializer = SolicitarCodigoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        usuario = Usuario.objects.filter(
            email__iexact=serializer.validated_data['email'],
            activo=True,
        ).first()
        if usuario is None:
            return Response(
                {'error': 'No existe un usuario activo con ese correo.'},
                status=status.HTTP_404_NOT_FOUND,
            )

        codigo = f'{secrets.randbelow(1_000_000):06d}'
        codigo_hash = make_password(codigo)
        expiracion = timezone.now() + CODIGO_EXPIRACION

        RecuperacionContrasena.objects.update_or_create(
            usuario=usuario,
            defaults={
                'codigo_hash': codigo_hash,
                'codigo_expira_en': expiracion,
                'token_nonce': None,
                'token_expira_en': None,
            },
        )

        try:
            enviados = send_mail(
                subject='Código para restablecer tu contraseña',
                message=(
                    f'Tu código de recuperación para Echo es: {codigo}\n'
                    'Este código vence en 3 minutos. Si no solicitaste este cambio, '
                    'puedes ignorar este correo.'
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[usuario.email],
                fail_silently=False,
                html_message=(
                    '<div style="font-family:Arial,sans-serif;max-width:560px;'
                    'margin:24px auto;padding:32px;border:1px solid #e5e7eb;'
                    'border-radius:12px;color:#1f2937">'
                    '<h1 style="color:#4f46e5;margin:0 0 16px">Echo</h1>'
                    '<h2 style="margin:0 0 12px">Restablece tu contraseña</h2>'
                    '<p>Usa este código para continuar con la recuperación de tu cuenta:</p>'
                    f'<p style="font-size:32px;font-weight:bold;letter-spacing:8px;'
                    f'color:#4f46e5;margin:24px 0">{codigo}</p>'
                    '<p>El código vence en <strong>3 minutos</strong>.</p>'
                    '<p style="font-size:13px;color:#6b7280">Si no solicitaste este cambio, '
                    'ignora este correo. Tu contraseña no cambiará.</p>'
                    '</div>'
                ),
            )
        except (BadHeaderError, OSError, smtplib.SMTPException):
            logger.exception('No se pudo enviar el código de recuperación.')
            RecuperacionContrasena.objects.filter(
                usuario=usuario,
                codigo_hash=codigo_hash,
            ).delete()
            return Response(
                {'error': 'No fue posible enviar el correo de recuperación.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if enviados != 1:
            logger.error('El backend de correo no confirmó el envío del código.')
            RecuperacionContrasena.objects.filter(
                usuario=usuario,
                codigo_hash=codigo_hash,
            ).delete()
            return Response(
                {'error': 'No fue posible enviar el correo de recuperación.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(
            {
                'mensaje': 'Código enviado con éxito',
                'expira_en': 3,
                'expires_at': 3,
                'tiempo_expiracion': 3,
                'exp': 3,
            },
            status=status.HTTP_200_OK,
        )


class VerificarCodigoAPIView(RecuperacionAPIView):
    def post(self, request):
        serializer = VerificarCodigoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            usuario = Usuario.objects.get(
                email__iexact=serializer.validated_data['email'],
                activo=True,
            )
            recuperacion = RecuperacionContrasena.objects.get(usuario=usuario)
        except (Usuario.DoesNotExist, RecuperacionContrasena.DoesNotExist):
            return Response(
                {'error': 'El código es inválido o expiró.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            recuperacion.codigo_expira_en is None
            or recuperacion.codigo_expira_en <= timezone.now()
            or not check_password(serializer.validated_data['codigo'], recuperacion.codigo_hash)
        ):
            return Response(
                {'error': 'El código es inválido o expiró.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        nonce = uuid.uuid4()
        token_expira_en = timezone.now() + TOKEN_EXPIRACION
        recuperacion.token_nonce = nonce
        recuperacion.token_expira_en = token_expira_en
        recuperacion.codigo_hash = ''
        recuperacion.codigo_expira_en = None
        recuperacion.save(
            update_fields=[
                'codigo_hash',
                'codigo_expira_en',
                'token_nonce',
                'token_expira_en',
            ]
        )

        token = signing.dumps(
            {'user_id': usuario.pk, 'nonce': str(nonce)},
            salt=TOKEN_SALT,
            compress=True,
        )
        return Response(
            {
                'mensaje': 'Código verificado correctamente',
                'token': token,
                'access_token': token,
                'temp_token': token,
            },
            status=status.HTTP_200_OK,
        )


class RestablecerContrasenaAPIView(RecuperacionAPIView):
    def post(self, request):
        cabecera = request.headers.get('Authorization', '')
        esquema, _, token = cabecera.partition(' ')
        if cabecera and (esquema.lower() != 'bearer' or not token):
            return Response(
                {'error': 'Debes enviar un token Bearer válido.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        datos = request.data.copy()
        if not datos.get('token') and token:
            datos['token'] = token
        serializer = RestablecerContrasenaSerializer(data=datos)
        serializer.is_valid(raise_exception=True)
        token = token or serializer.validated_data['token']

        try:
            datos_token = signing.loads(
                token,
                salt=TOKEN_SALT,
                max_age=int(TOKEN_EXPIRACION.total_seconds()),
            )
            usuario_id = datos_token['user_id']
            nonce = uuid.UUID(datos_token['nonce'])
        except (signing.BadSignature, KeyError, TypeError, ValueError):
            return Response(
                {'error': 'El token de recuperación es inválido o expiró.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        with transaction.atomic():
            try:
                recuperacion = (
                    RecuperacionContrasena.objects.select_for_update()
                    .select_related('usuario')
                    .get(usuario_id=usuario_id)
                )
            except RecuperacionContrasena.DoesNotExist:
                return Response(
                    {'error': 'El token de recuperación es inválido o expiró.'},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            if (
                not recuperacion.usuario.activo
                or recuperacion.token_nonce != nonce
                or recuperacion.token_expira_en is None
                or recuperacion.token_expira_en <= timezone.now()
            ):
                return Response(
                    {'error': 'El token de recuperación es inválido o expiró.'},
                    status=status.HTTP_401_UNAUTHORIZED,
                )

            try:
                validate_password(serializer.validated_data['password'], recuperacion.usuario)
            except ValidationError as error:
                return Response(
                    {'password': error.messages},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            recuperacion.usuario.set_password(serializer.validated_data['password'])
            recuperacion.usuario.save(update_fields=['password'])
            recuperacion.delete()

        return Response(
            {'mensaje': 'La contraseña se restableció correctamente.'},
            status=status.HTTP_200_OK,
        )
