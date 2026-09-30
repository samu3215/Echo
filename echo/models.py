from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import F, Q, CheckConstraint, UniqueConstraint

class Usuario(models.Model):
    TIPO_USUARIO_CHOICES = [
        ('normal', 'Normal'),
        ('empresarial', 'Empresarial'),
    ]
    
    email = models.EmailField(max_length=100, unique=True)
    nombre_usuario = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255) 
    tipo_usuario = models.CharField(max_length=15, choices=TIPO_USUARIO_CHOICES)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    activo = models.BooleanField(default=True)
    foto_perfil = models.CharField(max_length=255, blank=True, null=True)

    nombre = models.CharField(max_length=100, blank=True, null=True)
    apellido = models.CharField(max_length=100, blank=True, null=True)
    nombre_negocio = models.CharField(max_length=100, blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    direccion = models.CharField(max_length=150, blank=True, null=True)
    telefono = models.CharField(max_length=10, blank=True, null=True, unique=True)

    def __str__(self):
        return self.nombre_usuario

    def save(self, *args, **kwargs):
        if self.telefono == "":
            self.telefono = None
        super().save(*args, **kwargs)

class Seguidor(models.Model):
    seguidor = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='siguiendo')
    seguido = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='seguidores')
    fecha_seguimiento = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['seguidor', 'seguido'], name='seguimiento_unico'),
            CheckConstraint(condition=~Q(seguidor=F('seguido')), name='evitar_autoseguimiento')
        ]

class Publicacion(models.Model):
    TIPO_MEDIA_CHOICES = [
        ('texto', 'Texto'),
        ('imagen', 'Imagen'),
        ('video', 'Video'),
    ]
    contenido = models.TextField(blank=True, null=True)
    url_media = models.CharField(max_length=255, blank=True, null=True)
    tipo_media = models.CharField(max_length=10, choices=TIPO_MEDIA_CHOICES, default='texto')
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='publicaciones')

class Comentario(models.Model):
    contenido = models.TextField()
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='comentarios')
    publicacion = models.ForeignKey(Publicacion, on_delete=models.CASCADE, related_name='comentarios_publicacion')

class Like(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='likes')
    publicacion = models.ForeignKey(Publicacion, on_delete=models.CASCADE, related_name='likes_publicacion')
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['usuario', 'publicacion'], name='like_unico')
        ]

class Comunidad(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    categoria = models.CharField(max_length=50, blank=True, null=True)
    foto_comunidad = models.CharField(max_length=255, blank=True, null=True)
    activo = models.BooleanField(default=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='comunidades_creadas')
    fecha_creacion = models.DateTimeField(auto_now_add=True)

class UsuarioComunidad(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='comunidades_unidas')
    comunidad = models.ForeignKey(Comunidad, on_delete=models.CASCADE, related_name='miembros')
    fecha_union = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['usuario', 'comunidad'], name='union_unica')
        ]

class MensajeComunidad(models.Model):
    contenido = models.TextField(blank=True, null=True)
    url_media = models.CharField(max_length=255, blank=True, null=True)
    fecha_envio = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)   
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='mensajes_comunidad')
    comunidad = models.ForeignKey(Comunidad, on_delete=models.CASCADE, related_name='mensajes')
    publicacion_reenviada = models.ForeignKey(Publicacion, on_delete=models.SET_NULL, blank=True, null=True, related_name='reenvios_comunidad')
    mensaje_respondido = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='respuestas')

class Calificacion(models.Model):
    puntuacion = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    descripcion = models.TextField(blank=True, null=True)
    
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    
    usuario_califica = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='calificaciones_dadas')
    usuario_calificado = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='calificaciones_recibidas')

    class Meta:
        constraints = [
            UniqueConstraint(fields=['usuario_califica', 'usuario_calificado'], name='calificacion_unica'),
            CheckConstraint(condition=~Q(usuario_califica=F('usuario_calificado')), name='evitar_autocalificacion')
        ]










class Notificacion(models.Model):
    TIPO_CHOICES = [
        ('like', 'Like'),
        ('comentario', 'Comentario'),
        ('seguidor', 'Nuevo seguidor'),
        ('calificacion', 'Nueva calificación'),
    ]

    usuario = models.ForeignKey(
        Usuario,
        on_delete=models.CASCADE,
        related_name='notificaciones'
    )

    mensaje = models.CharField(max_length=255)

    tipo = models.CharField(
        max_length=20,
        choices=TIPO_CHOICES
    )

    leida = models.BooleanField(default=False)

    fecha_creacion = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.mensaje