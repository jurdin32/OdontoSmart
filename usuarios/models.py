from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver


class Role(models.Model):
    """Modelo para gestionar roles de usuario"""
    class Meta:
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'

    ADMIN = 'ADMIN'
    DOCTOR = 'DOCTOR'
    ASSISTANT = 'ASSISTANT'
    PATIENT = 'PATIENT'

    ROLE_CHOICES = [
        (ADMIN, 'Administrador'),
        (DOCTOR, 'Odontólogo'),
        (ASSISTANT, 'Asistente'),
        (PATIENT, 'Paciente'),
    ]

    nombre = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        unique=True,
        verbose_name='Nombre del rol'
    )
    descripcion = models.TextField(blank=True, verbose_name='Descripción')

    def __str__(self):
        return self.get_nombre_display()


class Profile(models.Model):
    """Perfil extendido del usuario con información del consultorio"""
    class Meta:
        verbose_name = 'Perfil'
        verbose_name_plural = 'Perfiles'

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='Usuario'
    )
    empresa = models.ForeignKey(
        'core.Empresa',
        on_delete=models.CASCADE,
        null=True, blank=True,
        verbose_name='Empresa'
    )
    rol = models.ForeignKey(
        Role,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Rol'
    )
    telefono = models.CharField(
        max_length=20,
        blank=True,
        verbose_name='Teléfono'
    )
    direccion = models.TextField(blank=True, verbose_name='Dirección')
    foto = models.ImageField(
        upload_to='perfiles/',
        blank=True,
        null=True,
        verbose_name='Foto de perfil'
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de registro'
    )

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.rol}"


# Señal para crear perfil automáticamente al crear usuario
@receiver(post_save, sender=User)
def crear_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        # Modo clínica única: el perfil se asocia a la clínica del sistema
        from core.models import Empresa
        Profile.objects.create(user=instance, empresa=Empresa.get_solo())


@receiver(post_save, sender=User)
def guardar_perfil_usuario(sender, instance, **kwargs):
    instance.profile.save()


class ActivityLog(models.Model):
    """Registro de actividad del sistema"""
    class Meta:
        verbose_name = 'Actividad'
        verbose_name_plural = 'Actividades'
        ordering = ['-fecha']

    ACCION_CHOICES = [
        ('CREAR', 'Creación'),
        ('EDITAR', 'Edición'),
        ('ELIMINAR', 'Eliminación'),
        ('LOGIN', 'Inicio de sesión'),
    ]

    empresa = models.ForeignKey(
        'core.Empresa', on_delete=models.CASCADE,
        null=True, blank=True, verbose_name='Empresa'
    )
    usuario = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, verbose_name='Usuario'
    )
    accion = models.CharField(
        max_length=20, choices=ACCION_CHOICES, verbose_name='Acción'
    )
    modelo = models.CharField(max_length=50, verbose_name='Modelo')
    objeto_id = models.PositiveIntegerField(null=True, blank=True)
    descripcion = models.CharField(
        max_length=255, verbose_name='Descripción'
    )
    fecha = models.DateTimeField(auto_now_add=True, verbose_name='Fecha')

    def __str__(self):
        return f'{self.usuario} - {self.accion} - {self.descripcion}'
