"""
Generación de XML para facturación electrónica SRI Ecuador.

Basado en:
  - Esquema XSD del SRI factura_1.0.0.xsd / factura_1.1.0.xsd
  - Ficha Técnica de Comprobantes Electrónicos Esquema Off-line v2.33
  - XML de factura firmada oficial del SRI

Usa lxml en lugar de minidom para garantizar salida C14N-compatible,
necesaria para el cálculo correcto del digest en la firma XAdES-BES.
"""

from datetime import datetime
from decimal import Decimal
from lxml import etree

from . import enums
from .utils import (
    generar_clave_acceso,
    serializar_numero,
    get_identificacion_tipo,
    get_codigo_porcentaje_iva,
    get_tarifa_iva,
)


def xml_factura(
    config: object,  # SriEmpresaConfig
    factura_data: dict,
    secuencial: str = None,
) -> tuple:
    """
    Genera el XML de una factura electrónica SRI.

    Args:
        config: SriEmpresaConfig con datos del emisor
        factura_data: dict con datos de la factura:
            - fecha_emision: datetime
            - cliente_identificacion: str
            - cliente_razon_social: str
            - cliente_direccion: str (opcional)
            - cliente_email: str (opcional)
            - items: list[dict]
            - subtotal, descuento, iva_porcentaje, iva_valor, total: Decimal
            - forma_pago_sri: str (código SRI)
        secuencial: str (opcional, 9 dígitos)

    Returns:
        tuple: (clave_acceso, numero_documento, xml_string)
    """
    from django.utils import timezone

    now = factura_data.get('fecha_emision', timezone.localtime())
    sec = secuencial or '000000001'
    numero_doc = serializar_numero(
        config.estab_factura, config.emision_factura, sec
    )
    ambiente = config.ambiente

    clave = generar_clave_acceso(
        ruc=config.ruc,
        tipo_documento=enums.DOC_FACTURA,
        serie=numero_doc,
        secuencial=sec,
        fecha_emision=now,
        ambiente=ambiente,
    )

    # Versión según tipo de contribuyente (Ficha Técnica SRI v2.33)
    version_sri = '1.1.0' if config.tipo_contribuyente in (
        'RIMPE_NEGOCIO_POPULAR', 'RIMPE_EMPRENDEDOR', 'AGENTE_RETENCION'
    ) else '1.0.0'

    # ====================================================================
    # Construir XML con lxml (etree)
    # ====================================================================
    factura = etree.Element('factura', id='comprobante', version=version_sri)

    # ==================== INFO TRIBUTARIA ====================
    info_trib = etree.SubElement(factura, 'infoTributaria')
    _el(info_trib, 'ambiente', ambiente)
    _el(info_trib, 'tipoEmision', enums.EMISION_NORMAL)
    _el(info_trib, 'razonSocial', config.razon_social)
    if config.nombre_comercial:
        _el(info_trib, 'nombreComercial', config.nombre_comercial)
    _el(info_trib, 'ruc', config.ruc)
    _el(info_trib, 'claveAcceso', clave)
    _el(info_trib, 'codDoc', enums.DOC_FACTURA)
    _el(info_trib, 'estab', config.estab_factura.zfill(3))
    _el(info_trib, 'ptoEmi', config.emision_factura.zfill(3))
    _el(info_trib, 'secuencial', sec.zfill(9))
    _el(info_trib, 'dirMatriz', config.direccion or '')
    if version_sri == '1.1.0':
        if config.tipo_contribuyente == 'RIMPE_NEGOCIO_POPULAR':
            _el(info_trib, 'contribuyenteRimpe',
                'CONTRIBUYENTE NEGOCIO POPULAR - RÉGIMEN RIMPE')
        elif config.tipo_contribuyente == 'RIMPE_EMPRENDEDOR':
            _el(info_trib, 'contribuyenteRimpe',
                'CONTRIBUYENTE RÉGIMEN RIMPE')
        elif config.tipo_contribuyente == 'AGENTE_RETENCION':
            _el(info_trib, 'contribuyenteRimpe',
                'AGENTE DE RETENCIÓN')

    # ==================== INFO FACTURA ====================
    info_fac = etree.SubElement(factura, 'infoFactura')

    fecha_str = now.strftime('%d/%m/%Y')
    _el(info_fac, 'fechaEmision', fecha_str)
    _el(info_fac, 'dirEstablecimiento',
        config.direccion or config.razon_social or 'MATRIZ')

    if config.contribuyente_especial:
        _el(info_fac, 'contribuyenteEspecial', config.contribuyente_especial)

    _el(info_fac, 'obligadoContabilidad',
        'SI' if config.obligado_contabilidad else 'NO')

    tipo_id = get_identificacion_tipo(
        factura_data.get('cliente_identificacion', '')
    )
    _el(info_fac, 'tipoIdentificacionComprador', tipo_id)
    _el(info_fac, 'razonSocialComprador',
        factura_data.get('cliente_razon_social', ''))
    _el(info_fac, 'identificacionComprador',
        factura_data.get('cliente_identificacion', ''))

    if factura_data.get('cliente_direccion'):
        _el(info_fac, 'direccionComprador',
            factura_data['cliente_direccion'])

    _el(info_fac, 'totalSinImpuestos',
        _fmt(factura_data.get('subtotal', 0)))
    _el(info_fac, 'totalDescuento',
        _fmt(factura_data.get('descuento', 0)))

    # Total con impuestos
    iva_pct = float(factura_data.get('iva_porcentaje', 0))
    iva_valor = float(factura_data.get('iva_valor', 0))
    codigo_pct = get_codigo_porcentaje_iva(iva_pct)

    total_con_impuestos = etree.SubElement(info_fac, 'totalConImpuestos')
    impuesto = etree.SubElement(total_con_impuestos, 'totalImpuesto')
    _el(impuesto, 'codigo', enums.IMP_IVA)
    _el(impuesto, 'codigoPorcentaje', codigo_pct)
    _el(impuesto, 'baseImponible', _fmt(factura_data.get('subtotal', 0)))
    _el(impuesto, 'valor', _fmt(iva_valor))

    # Propina (valor entero 0 según XML oficial SRI)
    _el(info_fac, 'propina', '0')

    _el(info_fac, 'importeTotal', _fmt(factura_data.get('total', 0)))
    _el(info_fac, 'moneda', 'DOLAR')

    # Pagos
    pagos = etree.SubElement(info_fac, 'pagos')
    pago = etree.SubElement(pagos, 'pago')
    _el(pago, 'formaPago',
        factura_data.get('forma_pago_sri', enums.PAGO_SIN_UTILIZACION))
    _el(pago, 'total', _fmt(factura_data.get('total', 0)))
    _el(pago, 'plazo', '0')
    _el(pago, 'unidadTiempo', 'dias')

    # ==================== DETALLES ====================
    detalles = etree.SubElement(factura, 'detalles')

    items = factura_data.get('items', [])
    for i, item in enumerate(items, 1):
        detalle = etree.SubElement(detalles, 'detalle')

        _el(detalle, 'codigoPrincipal', str(i).zfill(3))
        if item.get('codigo_auxiliar'):
            _el(detalle, 'codigoAuxiliar', item['codigo_auxiliar'])
        _el(detalle, 'descripcion', item.get('descripcion', ''))
        _el(detalle, 'cantidad', _fmt(item.get('cantidad', 1)))
        _el(detalle, 'precioUnitario', _fmt(item.get('precio_unitario', 0)))
        _el(detalle, 'descuento', _fmt(item.get('descuento_item', 0)))
        _el(detalle, 'precioTotalSinImpuesto', _fmt(item.get('total', 0)))

        # Impuestos del ítem
        impuestos_item = etree.SubElement(detalle, 'impuestos')
        imp_item = etree.SubElement(impuestos_item, 'impuesto')

        _el(imp_item, 'codigo', enums.IMP_IVA)
        _el(imp_item, 'codigoPorcentaje', codigo_pct)
        _el(imp_item, 'tarifa', get_tarifa_iva(iva_pct))
        base_imponible_item = float(item.get('total', 0))
        valor_iva_item = (
            round(base_imponible_item * iva_pct / 100, 2)
            if iva_pct > 0 else 0
        )
        _el(imp_item, 'baseImponible', _fmt(base_imponible_item))
        _el(imp_item, 'valor', _fmt(valor_iva_item))

    # ==================== INFORMACIÓN ADICIONAL ====================
    info_adicional = etree.SubElement(factura, 'infoAdicional')

    if factura_data.get('cliente_direccion'):
        campo = etree.SubElement(
            info_adicional, 'campoAdicional', nombre='Dirección'
        )
        campo.text = factura_data['cliente_direccion']

    if factura_data.get('cliente_telefono'):
        campo = etree.SubElement(
            info_adicional, 'campoAdicional', nombre='Teléfono'
        )
        campo.text = factura_data['cliente_telefono']

    if factura_data.get('cliente_email'):
        campo = etree.SubElement(
            info_adicional, 'campoAdicional', nombre='Email'
        )
        campo.text = factura_data['cliente_email']

    # ====================================================================
    # Serializar XML (SIN indentación para compatibilidad C14N)
    # ====================================================================
    xml_bytes = etree.tostring(
        factura, xml_declaration=True, encoding='UTF-8', pretty_print=False
    )
    xml_str = xml_bytes.decode('UTF-8')

    return clave, numero_doc, xml_str


def _el(parent, tag, text=None):
    """Crea un elemento hijo con texto opcional."""
    elem = etree.SubElement(parent, tag)
    if text is not None:
        elem.text = str(text)
    return elem


def _fmt(valor) -> str:
    """Formatea un valor numérico a 2 decimales."""
    try:
        return f'{float(valor):.2f}'
    except (TypeError, ValueError):
        return '0.00'
