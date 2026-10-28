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
    es_admin = models.BooleanField(default=False)
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
    descripcion = models.TextField(blank=True, null=True)
    comentarios_activados = models.BooleanField(default=True)
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='publicaciones')

    def __str__(self):
        return f"Publicacion de {self.usuario.nombre_usuario}"

class ArchivoPublicacion(models.Model):
    TIPO_MEDIA_CHOICES = [
        ('imagen', 'Imagen'),
        ('video', 'Video'),
    ]
    publicacion = models.ForeignKey(Publicacion, on_delete=models.CASCADE, related_name='archivos')
    url_media = models.CharField(max_length=255)
    tipo_media = models.CharField(max_length=10, choices=TIPO_MEDIA_CHOICES)
    
    orden = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ['orden']
        constraints = [
            UniqueConstraint(fields=['publicacion', 'orden'], name='orden_unico_por_publicacion')
        ]

class Comentario(models.Model):
    contenido = models.TextField()
    
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)

    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='comentarios')
    publicacion = models.ForeignKey(Publicacion, on_delete=models.CASCADE, related_name='comentarios_publicacion')
    comentario_padre = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='respuestas')

class Like(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='likes')
    publicacion = models.ForeignKey(Publicacion, on_delete=models.CASCADE, related_name='likes_publicacion')
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['usuario', 'publicacion'], name='like_unico')
        ]

class Comunidad(models.Model):
    
    CATEGORIAS_CHOICES = [
        ('tecnologia', 'Tecnología y Programaciónp'),
        ('videojuegos', 'Videojuegos y Gaming'),
        ('arte', 'Arte y Diseño'),
        ('musica', 'Música y Entretenimiento'),
        ('deportes', 'Deportes y Salud'),
        ('educacion', 'Educación y Aprendizaje'),
        ('negocios', 'Negocios y Emprendimiento'),
        ('general', 'General / Otros'),
    ]

    nombre = models.CharField(max_length=255)
    descripcion = models.TextField(blank=True, null=True)
    categoria = models.CharField(max_length=50, choices=CATEGORIAS_CHOICES)
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
    
    fecha_envio = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    activo = models.BooleanField(default=True)   
    
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='mensajes_comunidad')
    comunidad = models.ForeignKey(Comunidad, on_delete=models.CASCADE, related_name='mensajes')
    
    publicacion_reenviada = models.ForeignKey('Publicacion', on_delete=models.SET_NULL, blank=True, null=True, related_name='reenvios_comunidad')
    mensaje_respondido = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True, related_name='respuestas')


class ArchivoMensaje(models.Model):
    TIPO_MEDIA_CHOICES = [
        ('imagen', 'Imagen'),
        ('video', 'Video')
    ]
    mensaje = models.ForeignKey(MensajeComunidad, on_delete=models.CASCADE, related_name='archivos')
    url_media = models.CharField(max_length=255)
    tipo_media = models.CharField(max_length=15, choices=TIPO_MEDIA_CHOICES)

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


class Reporte(models.Model):
    MOTIVOS_CHOICES = [
        ('ilegal', 'Contenido Ilegal o Violento'),
        ('abuso', 'Abuso / Acoso Grave'),
        ('spam', 'Spam / Estafa'),
    ]
    
    publicacion = models.ForeignKey('Publicacion', on_delete=models.CASCADE, related_name='reportes')
    usuario_reportado = models.ForeignKey('Usuario', on_delete=models.CASCADE, related_name='reportes_recibidos')
    usuario_reportador = models.ForeignKey('Usuario', on_delete=models.CASCADE, related_name='reportes_hechos')
    
    motivo = models.CharField(max_length=50, choices=MOTIVOS_CHOICES)
    fecha_reporte = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['publicacion', 'usuario_reportador'], name='reporte_unico')
        ]


class Notificacion(models.Model):
    TIPO_CHOICES = [
        ('seguimiento', 'Nuevo Seguidor'),
        ('calificacion', 'Nueva Calificación'),
    ]
    
    usuario_destino = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='notificaciones_recibidas')
    usuario_origen = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='notificaciones_enviadas')
    
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES)
    puntuacion = models.IntegerField(null=True, blank=True)
    leido = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

