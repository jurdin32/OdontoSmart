from django.db import models
from django.contrib.auth.models import User


class Medico(models.Model):
    """Modelo de médicos/odontólogos"""

    class Meta:
        verbose_name = 'Médico'
        verbose_name_plural = 'Médicos'
        ordering = ['apellidos', 'nombres']
        unique_together = [
            ('empresa', 'cedula'),
            ('empresa', 'registro_profesional'),
        ]

    ESPECIALIDADES = [
        ('ODONTO_GENERAL', 'Odontología General'),
        ('ORTODONCIA', 'Ortodoncia'),
        ('ENDODONCIA', 'Endodoncia'),
        ('PERIODONCIA', 'Periodoncia'),
        ('CIRUGIA_ORAL', 'Cirugía Oral'),
        ('IMPLANTOLOGIA', 'Implantología'),
        ('PEDIATRIA', 'Odontopediatría'),
        ('ESTETICA', 'Odontología Estética'),
        ('RADIOLOGIA', 'Radiología Oral'),
    ]

    empresa = models.ForeignKey(
        'core.Empresa', on_delete=models.CASCADE,
        null=True, blank=True,
        verbose_name='Empresa'
    )
    user = models.OneToOneField(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='medico', verbose_name='Usuario'
    )
    nombres = models.CharField(max_length=100, verbose_name='Nombres')
    apellidos = models.CharField(max_length=100, verbose_name='Apellidos')
    cedula = models.CharField(
        max_length=20, verbose_name='Cédula'
    )
    especialidad = models.CharField(
        max_length=50, choices=ESPECIALIDADES, verbose_name='Especialidad'
    )
    registro_profesional = models.CharField(
        max_length=50, verbose_name='Registro Profesional'
    )
    telefono = models.CharField(max_length=20, verbose_name='Teléfono')
    email = models.EmailField(blank=True, verbose_name='Correo Electrónico')
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_registro = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de registro'
    )

    def __str__(self):
        return f'Dr. {self.nombres} {self.apellidos} \n {self.get_especialidad_display()}'

    @property
    def nombre_completo(self):
        return f'{self.nombres} {self.apellidos}'
