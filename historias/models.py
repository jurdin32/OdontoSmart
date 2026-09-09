from django.db import models
from django.contrib.auth.models import User
from pacientes.models import Paciente
from medicos.models import Medico

# ---------------------------------------------------------------------------
#  Mixin local para control de concurrencia en modelos de historias
# ---------------------------------------------------------------------------

class VersionModelMixin(models.Model):
    """Mixin abstracto que añade campo version y control de concurrencia."""
    version = models.PositiveIntegerField(
        default=1,
        verbose_name='Versión',
        help_text='Número de versión para control de concurrencia optimista'
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        skip_version_check = kwargs.pop('skip_version_check', False)
        if not skip_version_check and self.pk and self.version:
            from django.db import transaction
            with transaction.atomic():
                ModelClass = type(self)
                current = ModelClass.objects.select_for_update().filter(
                    pk=self.pk
                ).only('version').first()

                if current and current.version != self.version:
                    from core.concurrency import ConcurrentUpdateError
                    raise ConcurrentUpdateError(
                        ModelClass._meta.verbose_name or ModelClass.__name__,
                        self.pk, current.version, self.version
                    )
                nueva_version = (current.version if current else self.version) + 1
                self.version = nueva_version
                super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def save_without_version_check(self, *args, **kwargs):
        return self.save(*args, **kwargs, skip_version_check=True)


class Odontograma(VersionModelMixin):
    """Odontograma dental — un registro por historia"""

    class Meta:
        verbose_name = 'Odontograma'
        verbose_name_plural = 'Odontogramas'

    empresa = models.ForeignKey(
        'core.Empresa', on_delete=models.CASCADE,
        null=True, blank=True,
        verbose_name='Empresa'
    )
    historia = models.OneToOneField(
        'HistoriaClinica', on_delete=models.CASCADE,
        related_name='odontograma', verbose_name='Historia'
    )

    # Estado de cada diente (formato: { "18": "sano", "17": "caries", ... })
    # Posibles valores: sano, caries, ausente, obturado, corona, endodoncia, puente, implante
    dientes = models.JSONField(default=dict, verbose_name='Estado de dientes')

    # Indicaciones (colores)
    # Formato: { "18": {"existente": true, "requerido": false}, ... }
    prestaciones = models.JSONField(default=dict, verbose_name='Prestaciones')

    # Checkboxes inferiores
    protesis_fija = models.BooleanField(default=False, verbose_name='Prótesis fija')
    protesis_removible = models.BooleanField(default=False, verbose_name='Prótesis removible')
    coronas = models.BooleanField(default=False, verbose_name='Coronas')
    cantidad_dientes_existentes = models.PositiveIntegerField(
        null=True, blank=True, verbose_name='Cantidad de dientes existentes'
    )
    presencia_sarro = models.BooleanField(default=False, verbose_name='Presencia de sarro')
    enfermedad_periodontal = models.BooleanField(default=False, verbose_name='Enfermedad periodontal')

    def __str__(self):
        return f'Odontograma de {self.historia.paciente}'


class HistoriaClinica(VersionModelMixin):
    """Historia clínica general del paciente (uno por paciente)"""

    class Meta:
        verbose_name = 'Historia Clínica'
        verbose_name_plural = 'Historias Clínicas'

    SANGRE_CHOICES = [
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    ]

    empresa = models.ForeignKey(
        'core.Empresa', on_delete=models.CASCADE,
        null=True, blank=True,
        verbose_name='Empresa'
    )
    # Relación
    paciente = models.OneToOneField(
        Paciente, on_delete=models.CASCADE,
        related_name='historia', verbose_name='Paciente'
    )

    # Antecedentes personales (Preguntas Si/No de la ficha)
    alergia_drogas = models.BooleanField(
        default=False, verbose_name='¿Es alérgico a alguna droga?'
    )
    exceso_saliva = models.BooleanField(
        default=False, verbose_name='¿Tiene exceso de saliva en la anestesia?'
    )
    cicatrizacion = models.BooleanField(
        default=False, verbose_name='¿Cicatriza bien?'
    )
    sangrado = models.BooleanField(
        default=False, verbose_name='¿Sangra mucho?'
    )
    diabetes = models.BooleanField(default=False, verbose_name='¿Es diabético?')
    diabetes_controlado = models.CharField(
        max_length=100, blank=True,
        verbose_name='¿Está controlado? ¿Con qué?'
    )
    cardiacos = models.BooleanField(
        default=False, verbose_name='¿Tiene algún problema cardíaco?'
    )
    aspirina = models.BooleanField(
        default=False, verbose_name='¿Toma seguido aspirina y/o anticoagulante?'
    )
    frecuencia_aspirina = models.CharField(
        max_length=100, blank=True,
        verbose_name='¿Con qué frecuencia?'
    )
    alergias = models.BooleanField(default=False, verbose_name='Alergias')
    hipertension = models.BooleanField(default=False, verbose_name='Hipertensión')
    medicacion = models.BooleanField(default=False, verbose_name='Toma medicación')
    observaciones_medicas = models.TextField(
        blank=True, verbose_name='Observaciones médicas',
        help_text='Detalles adicionales sobre las condiciones marcadas'
    )
    tipo_sangre = models.CharField(
        max_length=3, blank=True,
        choices=SANGRE_CHOICES, verbose_name='Tipo de sangre'
    )

    # Hábitos
    fumador = models.BooleanField(default=False, verbose_name='Fumador')
    alcohol = models.BooleanField(default=False, verbose_name='Consume alcohol')
    embarazo = models.BooleanField(default=False, verbose_name='Embarazada')
    observaciones_habitos = models.TextField(
        blank=True, verbose_name='Observaciones de hábitos'
    )

    # Antecedentes familiares
    antecedentes_familiares = models.TextField(
        blank=True,
        verbose_name='Antecedentes familiares',
        help_text='Enfermedades relevantes en la familia'
    )

    # Diagnóstico y tratamiento
    diagnostico_presuntivo = models.TextField(
        blank=True, verbose_name='Diagnóstico presuntivo'
    )
    plan_tratamiento = models.TextField(
        blank=True, verbose_name='Plan de tratamiento'
    )
    observaciones = models.TextField(
        blank=True, verbose_name='Observaciones'
    )

    # Consentimiento informado
    consentimiento = models.BooleanField(
        default=False, verbose_name='Paciente acepta el tratamiento'
    )
    consentimiento_fecha = models.DateField(
        null=True, blank=True, verbose_name='Fecha de consentimiento'
    )
    consentimiento_paciente = models.CharField(
        max_length=200, blank=True, verbose_name='Nombre del paciente'
    )
    consentimiento_direccion = models.TextField(
        blank=True, verbose_name='Dirección'
    )
    consentimiento_cedula = models.CharField(
        max_length=20, blank=True, verbose_name='Cédula de identidad'
    )
    consentimiento_medico = models.CharField(
        max_length=200, blank=True, verbose_name='Médico que solicita el consentimiento'
    )

    # Metadatos
    registrado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        verbose_name='Registrado por'
    )
    fecha_creacion = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de creación'
    )
    fecha_actualizacion = models.DateTimeField(
        auto_now=True, verbose_name='Última actualización'
    )

    def __str__(self):
        return f'Historia de {self.paciente}'


class Evolucion(VersionModelMixin):
    """Evolución / consulta de la historia clínica"""

    class Meta:
        verbose_name = 'Evolución'
        verbose_name_plural = 'Evoluciones'
        ordering = ['-fecha']

    empresa = models.ForeignKey(
        'core.Empresa', on_delete=models.CASCADE,
        null=True, blank=True,
        verbose_name='Empresa'
    )
    historia = models.ForeignKey(
        HistoriaClinica, on_delete=models.CASCADE,
        related_name='evoluciones', verbose_name='Historia'
    )
    medico = models.ForeignKey(
        Medico, on_delete=models.SET_NULL, null=True,
        verbose_name='Médico'
    )
    fecha = models.DateField(verbose_name='Fecha de consulta')
    motivo = models.TextField(verbose_name='Motivo de consulta')
    diagnostico = models.TextField(blank=True, verbose_name='Diagnóstico')
    tratamiento = models.TextField(
        blank=True, verbose_name='Tratamiento / Procedimiento'
    )
    observaciones = models.TextField(
        blank=True, verbose_name='Observaciones'
    )

    # Consentimiento informado (por consulta)
    consentimiento_acepta = models.BooleanField(
        default=False, verbose_name='Paciente acepta el tratamiento'
    )
    consentimiento_fecha = models.DateField(
        null=True, blank=True, verbose_name='Fecha de consentimiento'
    )
    consentimiento_medico = models.CharField(
        max_length=200, blank=True,
        verbose_name='Médico que informa'
    )

    # Costo del tratamiento
    costo = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        verbose_name='Costo del tratamiento'
    )

    # Próxima consulta
    proxima_consulta = models.DateField(
        null=True, blank=True, verbose_name='Próxima consulta'
    )
    proxima_consulta_nota = models.CharField(
        max_length=255, blank=True,
        verbose_name='Nota para la próxima consulta'
    )

    registrado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True,
        verbose_name='Registrado por'
    )
    fecha_registro = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de registro'
    )

    def __str__(self):
        return f'{self.fecha} - {self.historia.paciente}'
