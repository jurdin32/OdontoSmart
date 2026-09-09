from django.db import models
from django.contrib.auth.models import User
from pacientes.models import Paciente
from medicos.models import Medico


class Cita(models.Model):
    """Modelo de citas odontológicas"""

    class Meta:
        verbose_name = 'Cita'
        verbose_name_plural = 'Citas'
        ordering = ['-fecha', '-hora']

    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('CONFIRMADA', 'Confirmada'),
        ('EN_CURSO', 'En Curso'),
        ('COMPLETADA', 'Completada'),
        ('CANCELADA', 'Cancelada'),
    ]

    empresa = models.ForeignKey(
        'core.Empresa', on_delete=models.CASCADE,
        null=True, blank=True,
        verbose_name='Empresa'
    )
    paciente = models.ForeignKey(
        Paciente, on_delete=models.CASCADE,
        related_name='citas', verbose_name='Paciente'
    )
    doctor = models.ForeignKey(
        Medico, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='citas', verbose_name='Doctor'
    )
    fecha = models.DateField(verbose_name='Fecha de la cita')
    hora = models.TimeField(verbose_name='Hora de la cita')
    motivo = models.TextField(verbose_name='Motivo de consulta')
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES,
        default='PENDIENTE', verbose_name='Estado'
    )
    notas = models.TextField(blank=True, verbose_name='Notas')
    registrado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='citas_creadas', verbose_name='Registrado por'
    )
    # ====== CONTROL DE CONCURRENCIA ======
    version = models.PositiveIntegerField(
        default=1,
        verbose_name='Versión',
        help_text='Número de versión para control de concurrencia optimista'
    )

    fecha_registro = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de registro'
    )
    fecha_actualizacion = models.DateTimeField(
        auto_now=True, verbose_name='Última actualización'
    )

    def save(self, *args, **kwargs):
        """Control de concurrencia optimista."""
        skip_version_check = kwargs.pop('skip_version_check', False)
        if not skip_version_check and self.pk and self.version:
            from django.db import transaction
            with transaction.atomic():
                current = Cita.objects.select_for_update().filter(
                    pk=self.pk
                ).only('version').first()

                if current and current.version != self.version:
                    from core.concurrency import ConcurrentUpdateError
                    raise ConcurrentUpdateError(
                        'Cita', self.pk, current.version, self.version
                    )
                nueva_version = (current.version if current else self.version) + 1
                self.version = nueva_version
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def save_without_version_check(self, *args, **kwargs):
        return self.save(*args, **kwargs, skip_version_check=True)

    def __str__(self):
        return f'{self.paciente} - {self.fecha} {self.hora}'
