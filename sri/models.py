from django.db import models
from django.utils import timezone


# ===========================================================================
#  CONFIGURACIÓN SRI POR EMPRESA
# ===========================================================================

class SriEmpresaConfig(models.Model):
    """Configuración SRI para una empresa (clínica/consultorio)."""

    class Meta:
        verbose_name = 'Configuración SRI'
        verbose_name_plural = 'Configuraciones SRI'

    empresa = models.OneToOneField(
        'core.Empresa', on_delete=models.CASCADE,
        related_name='sri_config', verbose_name='Empresa'
    )
    ruc = models.CharField(max_length=13, verbose_name='RUC')
    razon_social = models.CharField(max_length=300, verbose_name='Razón Social')
    nombre_comercial = models.CharField(
        max_length=300, blank=True, verbose_name='Nombre Comercial'
    )
    direccion = models.TextField(blank=True, verbose_name='Dirección')
    TIPO_CONTRIBUYENTE_CHOICES = [
        ('REGIMEN_GENERAL', 'Régimen General'),
        ('RIMPE_NEGOCIO_POPULAR', 'RIMPE - Negocio Popular'),
        ('RIMPE_EMPRENDEDOR', 'RIMPE - Emprendedor'),
        ('AGENTE_RETENCION', 'Agente de Retención'),
        ('CONTRIBUYENTE_ESPECIAL', 'Contribuyente Especial'),
    ]
    tipo_contribuyente = models.CharField(
        max_length=30, choices=TIPO_CONTRIBUYENTE_CHOICES,
        default='REGIMEN_GENERAL', verbose_name='Tipo de Contribuyente'
    )
    contribuyente_especial = models.CharField(
        max_length=4, blank=True, verbose_name='Resolución Contribuyente Especial'
    )
    obligado_contabilidad = models.BooleanField(
        default=True, verbose_name='Obligado a llevar contabilidad'
    )
    ambiente = models.CharField(
        max_length=1, choices=[('1', 'Pruebas'), ('2', 'Producción')],
        default='1', verbose_name='Ambiente SRI'
    )
    # Certificado digital (archivo .p12)
    certificado_p12 = models.FileField(
        upload_to='sri/certificados/', blank=True, null=True,
        verbose_name='Certificado Digital (.p12)',
        help_text='Archivo .p12 del certificado de firma electrónica'
    )
    clave_certificado = models.CharField(
        max_length=255, blank=True, verbose_name='Clave del Certificado',
        help_text='Contraseña del archivo .p12'
    )
    # Series de facturación (por establecimiento y punto de emisión)
    estab_factura = models.CharField(
        max_length=3, default='001', verbose_name='Establecimiento (Facturas)'
    )
    emision_factura = models.CharField(
        max_length=3, default='001', verbose_name='Punto de Emisión (Facturas)'
    )
    secuencial_factura = models.PositiveIntegerField(
        default=1, verbose_name='Secuencial actual (Facturas)'
    )
    resolucion_sri = models.CharField(
        max_length=50, blank=True, verbose_name='Resolución SRI',
        help_text='Número de resolución de la autorización SRI (offline)'
    )
    fecha_caducidad = models.DateField(
        null=True, blank=True, verbose_name='Fecha de caducidad',
        help_text='Fecha de caducidad de la autorización SRI'
    )
    # Comercio exterior (opcionales, para facturas de exportación)
    comercio_exterior = models.BooleanField(
        default=False, verbose_name='Comercio Exterior',
        help_text='SI/NO - Marcar si la factura es de exportación'
    )
    inco_term_factura = models.CharField(
        max_length=50, blank=True, verbose_name='Incoterm Factura',
        help_text='Término de negociación (ej: EXW, FOB, CIF)'
    )
    lugar_inco_term = models.CharField(
        max_length=100, blank=True, verbose_name='Lugar Incoterm',
        help_text='Lugar del término de negociación'
    )
    pais_origen = models.CharField(
        max_length=4, blank=True, verbose_name='País Origen',
        help_text='Código ISO del país de origen'
    )
    puerto_embarque = models.CharField(
        max_length=100, blank=True, verbose_name='Puerto de Embarque'
    )
    puerto_destino = models.CharField(
        max_length=100, blank=True, verbose_name='Puerto de Destino'
    )
    pais_destino = models.CharField(
        max_length=4, blank=True, verbose_name='País Destino',
        help_text='Código ISO del país de destino'
    )
    pais_adquisicion = models.CharField(
        max_length=4, blank=True, verbose_name='País de Adquisición',
        help_text='Código ISO del país de adquisición'
    )
    activo = models.BooleanField(default=True, verbose_name='Activo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'SRI - {self.razon_social}'

    @property
    def codigo_establecimiento(self):
        return self.estab_factura.zfill(3)

    @property
    def codigo_emision(self):
        return self.emision_factura.zfill(3)

    def peek_secuencial(self):
        """Obtiene el secuencial actual SIN incrementarlo (para reintentos)."""
        from django.db import transaction
        with transaction.atomic():
            config = SriEmpresaConfig.objects.select_for_update().get(pk=self.pk)
            return str(config.secuencial_factura).zfill(9)

    def consumir_secuencial(self):
        """Incrementa el secuencial (llamar SOLO cuando SRI confirma recepción)."""
        from django.db import transaction
        with transaction.atomic():
            config = SriEmpresaConfig.objects.select_for_update().get(pk=self.pk)
            config.secuencial_factura += 1
            config.save(update_fields=['secuencial_factura'])

    def next_secuencial(self):
        """Obtiene el siguiente secuencial y lo incrementa (forward-compat)."""
        sec = self.peek_secuencial()
        self.consumir_secuencial()
        return sec


# ===========================================================================
#  DOCUMENTO ELECTRÓNICO EMITIDO
# ===========================================================================

class SriDocumento(models.Model):
    """Registro de un documento electrónico emitido al SRI."""

    class Meta:
        verbose_name = 'Documento Electrónico'
        verbose_name_plural = 'Documentos Electrónicos'
        ordering = ['-created_at']

    TIPOS = [
        ('01', 'Factura'),
        ('04', 'Nota de Crédito'),
        ('05', 'Nota de Débito'),
        ('06', 'Guía de Remisión'),
        ('07', 'Comprobante de Retención'),
    ]

    ESTADOS = [
        ('PENDIENTE', 'Pendiente de envío'),
        ('ENVIADO', 'Enviado al SRI'),
        ('AUTORIZADO', 'Autorizado'),
        ('NO_AUTORIZADO', 'No autorizado'),
        ('ERROR', 'Error'),
    ]

    empresa_config = models.ForeignKey(
        SriEmpresaConfig, on_delete=models.CASCADE,
        related_name='documentos', verbose_name='Configuración SRI'
    )
    tipo = models.CharField(max_length=2, choices=TIPOS, verbose_name='Tipo')
    clave_acceso = models.CharField(
        max_length=49, unique=True, verbose_name='Clave de Acceso'
    )
    numero_documento = models.CharField(
        max_length=20, verbose_name='N° Documento',
        help_text='Formato: 001-001-000000001'
    )
    # Factura del sistema a la que corresponde (opcional para portabilidad)
    factura_origen_id = models.PositiveIntegerField(
        null=True, blank=True, verbose_name='ID Factura Origen'
    )
    factura_origen_modelo = models.CharField(
        max_length=100, blank=True, verbose_name='Modelo Factura Origen'
    )
    xml_firmado = models.TextField(blank=True, verbose_name='XML Firmado')
    archivo_xml_firmado = models.FileField(
        upload_to='sri/documentos/firmados/', blank=True, null=True,
        verbose_name='Archivo XML Firmado'
    )
    xml_autorizado = models.TextField(blank=True, verbose_name='XML Autorizado')
    archivo_xml_autorizado = models.FileField(
        upload_to='sri/documentos/autorizados/', blank=True, null=True,
        verbose_name='Archivo XML Autorizado'
    )
    numero_autorizacion = models.CharField(
        max_length=50, blank=True, verbose_name='N° Autorización SRI'
    )
    fecha_autorizacion = models.DateTimeField(
        null=True, blank=True, verbose_name='Fecha de Autorización'
    )
    ambiente = models.CharField(
        max_length=1, choices=[('1', 'Pruebas'), ('2', 'Producción')],
        verbose_name='Ambiente'
    )
    estado = models.CharField(
        max_length=20, choices=ESTADOS, default='PENDIENTE',
        verbose_name='Estado'
    )
    mensajes = models.JSONField(
        default=list, blank=True, verbose_name='Mensajes SRI'
    )
    # Datos del comprobante
    fecha_emision = models.DateTimeField(
        default=timezone.now, verbose_name='Fecha de emisión'
    )
    identificacion_comprador = models.CharField(
        max_length=20, blank=True, verbose_name='Identificación comprador'
    )
    razon_social_comprador = models.CharField(
        max_length=300, blank=True, verbose_name='Razón social comprador'
    )
    total_sin_impuestos = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Total sin impuestos'
    )
    total = models.DecimalField(
        max_digits=12, decimal_places=2, default=0,
        verbose_name='Total'
    )
    secuencial = models.CharField(
        max_length=9, blank=True, verbose_name='Secuencial usado',
        help_text='Secuencial de 9 dígitos usado para este documento'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.get_tipo_display()} {self.numero_documento} [{" / ".join(self.clave_acceso[i:i+8] for i in range(0, 49, 8))}]'

    @property
    def autorizado(self):
        return self.estado == 'AUTORIZADO'

    def marcar_autorizado(self, resultado, clave_acceso=None):
        """Registra la respuesta de autorización del SRI en este documento.

        Guarda estado, número de autorización, fecha de autorización y el XML
        autorizado. Devuelve `self` para encadenar `guardar_xml_autorizado()`.
        """
        from django.utils.dateparse import parse_datetime

        self.estado = 'AUTORIZADO'
        # El SRI devuelve el número de autorización (normalmente = clave de
        # acceso); si no lo manda, se usa la clave de acceso del documento.
        self.numero_autorizacion = (
            resultado.get('numero_autorizacion') or clave_acceso or self.clave_acceso
        )

        fecha = resultado.get('fecha_autorizacion')
        fecha_dt = None
        if isinstance(fecha, str) and fecha:
            fecha_dt = parse_datetime(fecha.replace('Z', '+00:00'))
        elif fecha:
            fecha_dt = fecha
        # Si el SRI no devuelve fecha, se registra el momento de la consulta
        self.fecha_autorizacion = fecha_dt or timezone.now()

        if resultado.get('xml_autorizado'):
            self.xml_autorizado = resultado['xml_autorizado']
        if resultado.get('mensajes'):
            self.mensajes = resultado['mensajes']
        return self

    def guardar_xml_autorizado(self):
        """Adjunta el XML autorizado como archivo. Devuelve el nombre o ''."""
        if not self.xml_autorizado:
            return ''
        from django.core.files.base import ContentFile

        nombre = f'sri_autorizado_{self.numero_documento.replace("-", "_")}.xml'
        if self.archivo_xml_autorizado:
            self.archivo_xml_autorizado.delete(save=False)
        self.archivo_xml_autorizado.save(
            nombre, ContentFile(self.xml_autorizado.encode('utf-8'))
        )
        return nombre
