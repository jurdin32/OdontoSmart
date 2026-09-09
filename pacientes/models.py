from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from datetime import date


class Paciente(models.Model):
    """Modelo principal del paciente"""

    class Meta:
        verbose_name = 'Paciente'
        verbose_name_plural = 'Pacientes'
        ordering = ['apellidos', 'nombres']
        unique_together = ('empresa', 'cedula')

    GENERO_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('O', 'Otro'),
    ]

    # ====== DATOS PERSONALES ======
    empresa = models.ForeignKey(
        'core.Empresa', on_delete=models.CASCADE,
        null=True, blank=True,
        verbose_name='Empresa'
    )
    nombres = models.CharField(max_length=100, verbose_name='Nombres')
    apellidos = models.CharField(max_length=100, verbose_name='Apellidos')
    cedula = models.CharField(
        max_length=20, verbose_name='Cédula / Documento'
    )
    fecha_nacimiento = models.DateField(verbose_name='Fecha de Nacimiento')
    edad = models.IntegerField(
        editable=False,
        verbose_name='Edad'
    )
    lugar = models.CharField(
        max_length=100, blank=True, verbose_name='Lugar'
    )
    nacionalidad = models.CharField(
        max_length=50, blank=True, verbose_name='Nacionalidad'
    )
    genero = models.CharField(
        max_length=1, choices=GENERO_CHOICES, verbose_name='Género'
    )
    telefono = models.CharField(max_length=20, verbose_name='Teléfono')
    celular = models.CharField(
        max_length=20, blank=True, verbose_name='Celular'
    )
    email = models.EmailField(blank=True, verbose_name='Correo Electrónico')
    direccion = models.TextField(blank=True, verbose_name='Dirección')
    ocupacion = models.CharField(
        max_length=100, blank=True, verbose_name='Ocupación'
    )
    foto = models.ImageField(
        upload_to='pacientes/',
        blank=True, null=True,
        verbose_name='Foto del paciente'
    )

    # ====== INFORMACIÓN DEL ACOMPAÑANTE ======
    acompanante_nombre = models.CharField(
        max_length=200, blank=True, verbose_name='Nombre del acompañante'
    )
    acompanante_telefono = models.CharField(
        max_length=20, blank=True, verbose_name='Teléfono del acompañante'
    )
    acompanante_parentesco = models.CharField(
        max_length=50, blank=True, verbose_name='Parentesco'
    )

    # ====== CONTROL DE CONCURRENCIA ======
    version = models.PositiveIntegerField(
        default=1,
        verbose_name='Versión',
        help_text='Número de versión para control de concurrencia optimista'
    )

    # ====== METADATOS ======
    fecha_registro = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de registro'
    )
    fecha_actualizacion = models.DateTimeField(
        auto_now=True, verbose_name='Última actualización'
    )
    registrado_por = models.ForeignKey(
        'auth.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='Registrado por'
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')

    def save(self, *args, **kwargs):
        """Calcula la edad automáticamente al guardar. Control de concurrencia optimista."""
        skip_version_check = kwargs.pop('skip_version_check', False)

        if self.fecha_nacimiento:
            today = date.today()
            self.edad = today.year - self.fecha_nacimiento.year - (
                (today.month, today.day) <
                (self.fecha_nacimiento.month, self.fecha_nacimiento.day)
            )

        if not skip_version_check and self.pk and self.version:
            from django.db import transaction
            with transaction.atomic():
                # Bloquea la fila y obtiene la versión actual en BD
                current = Paciente.objects.select_for_update().filter(
                    pk=self.pk
                ).only('version').first()

                if current and current.version != self.version:
                    from core.concurrency import ConcurrentUpdateError
                    raise ConcurrentUpdateError(
                        'Paciente', self.pk,
                        current.version, self.version
                    )
                # Versión coincide: incrementamos y guardamos
                nueva_version = (current.version if current else self.version) + 1
                self.version = nueva_version
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def save_without_version_check(self, *args, **kwargs):
        """Guarda sin verificar versión (para migraciones / tareas internas)."""
        return self.save(*args, **kwargs, skip_version_check=True)

    def __str__(self):
        return f"{self.nombres} {self.apellidos} \n {self.cedula}"

