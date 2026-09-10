from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from pacientes.models import Paciente
from medicos.models import Medico


# ===========================================================================
#  UTILITY: Generar número correlativo
# ===========================================================================

def generar_numero(tipo, empresa_id):
    """Genera el siguiente número correlativo para proformas o facturas."""
    from django.db.models import Max
    prefix = 'PRO' if tipo == 'proforma' else 'FAC'
    model = Proforma if tipo == 'proforma' else Factura
    ultimo = model.objects.filter(empresa_id=empresa_id).aggregate(
        max_num=Max('numero')
    )['max_num']
    if ultimo:
        try:
            num = int(ultimo.split('-')[1]) + 1
        except (IndexError, ValueError):
            num = 1
    else:
        num = 1
    return f'{prefix}-{num:04d}'


# ===========================================================================
#  SERVICIO (Catálogo de tratamientos / procedimientos)
# ===========================================================================

class Servicio(models.Model):
    """Servicio o tratamiento odontológico ofertado por la empresa."""

    class Meta:
        verbose_name = 'Servicio'
        verbose_name_plural = 'Servicios'
        ordering = ['nombre']
        unique_together = ('empresa', 'nombre')

    empresa = models.ForeignKey(
        'core.Empresa', on_delete=models.CASCADE,
        related_name='servicios', verbose_name='Empresa'
    )
    nombre = models.CharField(max_length=150, verbose_name='Nombre del servicio')
    descripcion = models.TextField(blank=True, verbose_name='Descripción')
    precio = models.DecimalField(
        max_digits=10, decimal_places=2, default=0,
        validators=[MinValueValidator(0)], verbose_name='Precio'
    )
    duracion_minutos = models.PositiveIntegerField(
        default=30, verbose_name='Duración (minutos)'
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')
    fecha_creacion = models.DateTimeField(
        auto_now_add=True, verbose_name='Fecha de creación'
    )
    fecha_actualizacion = models.DateTimeField(
        auto_now=True, verbose_name='Última actualización'
    )

    def __str__(self):
        return self.nombre


# ===========================================================================
#  PROFORMA (Cotización / Presupuesto)
# ===========================================================================

class Proforma(models.Model):
    """Presupuesto o cotización entregada al paciente."""

    class Meta:
        verbose_name = 'Proforma'
        verbose_name_plural = 'Proformas'
        ordering = ['-fecha_emision', '-id']

    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('APROBADA', 'Aprobada'),
        ('RECHAZADA', 'Rechazada'),
        ('VENCIDA', 'Vencida'),
        ('FACTURADA', 'Facturada'),
    ]

    empresa = models.ForeignKey(
        'core.Empresa', on_delete=models.CASCADE,
        null=True, blank=True, verbose_name='Empresa'
    )
    numero = models.CharField(
        max_length=20, unique=True, verbose_name='N° Proforma',
        help_text='Se genera automáticamente (ej: PRO-0001)'
    )
    paciente = models.ForeignKey(
        Paciente, on_delete=models.CASCADE,
        related_name='proformas', verbose_name='Paciente'
    )
    medico = models.ForeignKey(
        Medico, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='proformas', verbose_name='Médico'
    )
    fecha_emision = models.DateField(
        auto_now_add=True, verbose_name='Fecha de emisión'
    )
    fecha_validez = models.DateField(
        verbose_name='Válido hasta',
        help_text='Fecha hasta la cual el presupuesto tiene validez'
    )
    items = models.JSONField(
        default=list, verbose_name='Items',
        help_text='Lista de items: [{"descripcion": "...", "cantidad": 1, "precio_unitario": 0.00}]'
    )
    subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Subtotal'
    )
    descuento_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Descuento %'
    )
    descuento_monto = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Descuento $'
    )
    impuesto_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Impuesto %',
        help_text='Porcentaje de IVA u otro impuesto'
    )
    impuesto_monto = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Impuesto $'
    )
    total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Total'
    )
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES,
        default='PENDIENTE', verbose_name='Estado'
    )
    notas = models.TextField(
        blank=True, verbose_name='Notas',
        help_text='Condiciones, observaciones, etc.'
    )
    registrado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='proformas_creadas', verbose_name='Registrado por'
    )
    # ====== CONTROL DE CONCURRENCIA ======
    version = models.PositiveIntegerField(
        default=1, verbose_name='Versión'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado')

    def __str__(self):
        return f'{self.numero} - {self.paciente}'

    def save(self, *args, **kwargs):
        skip_version_check = kwargs.pop('skip_version_check', False)
        if not skip_version_check and self.pk and self.version:
            from django.db import transaction
            with transaction.atomic():
                current = Proforma.objects.select_for_update().filter(
                    pk=self.pk
                ).only('version').first()
                if current and current.version != self.version:
                    from core.concurrency import ConcurrentUpdateError
                    raise ConcurrentUpdateError(
                        'Proforma', self.pk, current.version, self.version
                    )
                nueva_version = (current.version if current else self.version) + 1
                self.version = nueva_version
                self._recalcular_totales()
                super().save(*args, **kwargs)
        else:
            if not self.pk:
                self._recalcular_totales()
            super().save(*args, **kwargs)

    def _recalcular_totales(self):
        """Recalcula subtotal, descuento, impuesto y total desde los items."""
        items = self.items or []
        self.subtotal = sum(
            float(item.get('cantidad', 0)) * float(item.get('precio_unitario', 0))
            for item in items
        )
        self.descuento_monto = round(
            float(self.subtotal) * (float(self.descuento_porcentaje) / 100), 2
        )
        base_imponible = float(self.subtotal) - float(self.descuento_monto)
        self.impuesto_monto = round(
            base_imponible * (float(self.impuesto_porcentaje) / 100), 2
        )
        self.total = round(base_imponible + float(self.impuesto_monto), 2)


# ===========================================================================
#  FACTURA
# ===========================================================================

# Valores de `SriDocumento.factura_origen_modelo` que apuntan a una Factura.
# El SRI guarda 'facturacion.factura'; se admite 'Factura' por datos antiguos.
MODELOS_SRI_FACTURA = ['facturacion.factura', 'Factura']


class Factura(models.Model):
    """Factura emitida al paciente por servicios odontológicos."""

    class Meta:
        verbose_name = 'Factura'
        verbose_name_plural = 'Facturas'
        ordering = ['-fecha_emision', '-id']

    ESTADO_CHOICES = [
        ('PENDIENTE', 'Pendiente'),
        ('PAGADA', 'Pagada'),
        ('ANULADA', 'Anulada'),
    ]

    FORMA_PAGO_CHOICES = [
        ('EFECTIVO', 'Efectivo'),
        ('TARJETA_CREDITO', 'Tarjeta de Crédito'),
        ('TARJETA_DEBITO', 'Tarjeta de Débito'),
        ('TRANSFERENCIA', 'Transferencia Bancaria'),
        ('CHEQUE', 'Cheque'),
        ('OTRO', 'Otro'),
    ]

    empresa = models.ForeignKey(
        'core.Empresa', on_delete=models.CASCADE,
        null=True, blank=True, verbose_name='Empresa'
    )
    numero = models.CharField(
        max_length=20, unique=True, verbose_name='N° Factura',
        help_text='Se genera automáticamente (ej: FAC-0001)'
    )
    proforma = models.ForeignKey(
        Proforma, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='facturas', verbose_name='Proforma origen'
    )
    paciente = models.ForeignKey(
        Paciente, on_delete=models.CASCADE,
        related_name='facturas', verbose_name='Paciente'
    )
    medico = models.ForeignKey(
        Medico, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='facturas', verbose_name='Médico'
    )
    fecha_emision = models.DateField(
        auto_now_add=True, verbose_name='Fecha de emisión'
    )
    fecha_pago = models.DateField(
        null=True, blank=True, verbose_name='Fecha de pago'
    )
    items = models.JSONField(
        default=list, verbose_name='Items',
        help_text='Lista de items: [{"descripcion": "...", "cantidad": 1, "precio_unitario": 0.00}]'
    )
    subtotal = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Subtotal'
    )
    descuento_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Descuento %'
    )
    descuento_monto = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Descuento $'
    )
    impuesto_porcentaje = models.DecimalField(
        max_digits=5, decimal_places=2, default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        verbose_name='Impuesto %'
    )
    impuesto_monto = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Impuesto $'
    )
    total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Total'
    )
    forma_pago = models.CharField(
        max_length=20, choices=FORMA_PAGO_CHOICES,
        default='EFECTIVO', verbose_name='Forma de pago'
    )
    estado = models.CharField(
        max_length=20, choices=ESTADO_CHOICES,
        default='PENDIENTE', verbose_name='Estado'
    )
    notas = models.TextField(
        blank=True, verbose_name='Notas'
    )
    registrado_por = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='facturas_creadas', verbose_name='Registrado por'
    )
    # ====== CONTROL DE CONCURRENCIA ======
    version = models.PositiveIntegerField(
        default=1, verbose_name='Versión'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Creado')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Actualizado')

    def __str__(self):
        return f'{self.numero} - {self.paciente}'

    def save(self, *args, **kwargs):
        skip_version_check = kwargs.pop('skip_version_check', False)
        if not skip_version_check and self.pk and self.version:
            from django.db import transaction
            with transaction.atomic():
                current = Factura.objects.select_for_update().filter(
                    pk=self.pk
                ).only('version').first()
                if current and current.version != self.version:
                    from core.concurrency import ConcurrentUpdateError
                    raise ConcurrentUpdateError(
                        'Factura', self.pk, current.version, self.version
                    )
                nueva_version = (current.version if current else self.version) + 1
                self.version = nueva_version
                self._recalcular_totales()
                super().save(*args, **kwargs)
        else:
            if not self.pk:
                self._recalcular_totales()
            super().save(*args, **kwargs)

    @property
    def sri_documento(self):
        """Documento SRI más reciente asociado a la factura (o None).

        Si el listado ya lo cargó con `set_sri_documento()` se reutiliza
        esa instancia en lugar de consultar la base de datos (evita N+1).
        """
        if 'sri_doc_prefetch' in self.__dict__:
            return self.__dict__['sri_doc_prefetch']
        return self.buscar_sri_documento()

    def set_sri_documento(self, doc):
        """Guarda el documento SRI en memoria para evitar consultas repetidas."""
        self.__dict__['sri_doc_prefetch'] = doc
        return self

    def buscar_sri_documento(self):
        """Consulta en BD el documento SRI más reciente de esta factura."""
        try:
            from sri.models import SriDocumento
            return SriDocumento.objects.filter(
                factura_origen_id=self.pk,
                factura_origen_modelo__in=MODELOS_SRI_FACTURA,
            ).order_by('-created_at').first()
        except Exception:
            return None

    @property
    def sri_estado_codigo(self):
        """Código del estado SRI ('AUTORIZADO', 'ERROR'…). Vacío si no se envió."""
        doc = self.sri_documento
        return doc.estado if doc else ''

    @property
    def sri_estado(self):
        """Retorna el estado SRI como texto amigable."""
        doc = self.sri_documento
        if not doc:
            return None
        return doc.get_estado_display()

    @property
    def sri_autorizado(self):
        """True si el SRI autorizó la factura."""
        return self.sri_estado_codigo == 'AUTORIZADO'

    @property
    def sri_numero_autorizacion(self):
        """N° de autorización del SRI (o la clave de acceso si aún no hay)."""
        doc = self.sri_documento
        if not doc:
            return ''
        return doc.numero_autorizacion or doc.clave_acceso or ''

    @property
    def sri_fecha_autorizacion(self):
        """Fecha/hora en que el SRI autorizó la factura, si existe."""
        doc = self.sri_documento
        if not doc:
            return None
        return doc.fecha_autorizacion

    @property
    def sri_clave_acceso(self):
        doc = self.sri_documento
        return doc.clave_acceso if doc else ''

    @property
    def sri_numero_documento(self):
        doc = self.sri_documento
        return doc.numero_documento if doc else ''

    @property
    def sri_mensajes(self):
        """Mensajes devueltos por el SRI para esta factura."""
        doc = self.sri_documento
        return list(doc.mensajes or []) if doc else []

    @property
    def sri_mensaje_error(self):
        """Texto del primer mensaje de error del SRI ('' si no hay)."""
        for msg in self.sri_mensajes:
            if (msg.get('tipo') or '').upper() in ('ERROR', 'ADVERTENCIA'):
                texto = msg.get('mensaje') or ''
                extra = msg.get('informacionAdicional') or ''
                return f'{texto} — {extra}' if extra else texto
        return ''

    @property
    def sri_color_clase(self):
        """Retorna la clase CSS para el badge SRI."""
        m = {
            'AUTORIZADO': 'success',
            'ENVIADO': 'warning',
            'PENDIENTE': 'secondary',
            'ERROR': 'danger',
            'NO_AUTORIZADO': 'danger',
        }
        return m.get(self.sri_estado_codigo, 'secondary')

    def _recalcular_totales(self):
        """Recalcula subtotal, descuento, impuesto y total desde los items."""
        items = self.items or []
        self.subtotal = sum(
            float(item.get('cantidad', 0)) * float(item.get('precio_unitario', 0))
            for item in items
        )
        self.descuento_monto = round(
            float(self.subtotal) * (float(self.descuento_porcentaje) / 100), 2
        )
        base_imponible = float(self.subtotal) - float(self.descuento_monto)
        self.impuesto_monto = round(
            base_imponible * (float(self.impuesto_porcentaje) / 100), 2
        )
        self.total = round(base_imponible + float(self.impuesto_monto), 2)
