"""
Catálogos SRI para facturación electrónica en Ecuador.
Basado en: https://www.sri.gob.ec/ facturación electrónica - catálogos
"""

# ===========================================================================
#  AMBIENTE (Entorno)
# ===========================================================================
AMBIENTE_PRUEBAS = '1'
AMBIENTE_PRODUCCION = '2'

AMBIENTES = {AMBIENTE_PRUEBAS: 'Pruebas', AMBIENTE_PRODUCCION: 'Producción'}

# ===========================================================================
#  TIPO DE EMISIÓN
# ===========================================================================
EMISION_NORMAL = '1'        # Online: se envía y autoriza inmediatamente
EMISION_INDISPONIBILIDAD = '2'  # Offline: se emite sin conexión y luego se autoriza

# ===========================================================================
#  TIPO DE DOCUMENTO
# ===========================================================================
DOC_FACTURA = '01'
DOC_NOTA_CREDITO = '04'
DOC_NOTA_DEBITO = '05'
DOC_GUIA_REMISION = '06'
DOC_COMPROBANTE_RETENCION = '07'

DOCUMENTOS = {
    DOC_FACTURA: 'Factura',
    DOC_NOTA_CREDITO: 'Nota de Crédito',
    DOC_NOTA_DEBITO: 'Nota de Débito',
    DOC_GUIA_REMISION: 'Guía de Remisión',
    DOC_COMPROBANTE_RETENCION: 'Comprobante de Retención',
}

# ===========================================================================
#  TIPO DE IDENTIFICACIÓN DEL EMISOR / ADQUIRENTE
# ===========================================================================
ID_RUC = '04'           # Registro Único de Contribuyentes
ID_CEDULA = '05'        # Cédula de identidad
ID_PASAPORTE = '06'     # Pasaporte
ID_CONSUMIDOR_FINAL = '07'  # Identificación del exterior / Consumidor final

TIPOS_IDENTIFICACION = {
    ID_RUC: 'RUC',
    ID_CEDULA: 'Cédula',
    ID_PASAPORTE: 'Pasaporte',
    ID_CONSUMIDOR_FINAL: 'Consumidor Final',
}

# ===========================================================================
#  TARIFA IVA
# ===========================================================================
TARIFA_IVA_0 = '0'     # 0%
TARIFA_IVA_12 = '2'    # 12% (histórico)
TARIFA_IVA_14 = '3'    # 14%
TARIFA_IVA_15 = '4'    # 15%
TARIFA_IVA_NO_OBJETO = '6'  # No objeto de IVA
TARIFA_IVA_EXENTO = '7'     # Exento de IVA

TARIFAS_IVA = {
    TARIFA_IVA_0: '0%',
    TARIFA_IVA_12: '12%',
    TARIFA_IVA_14: '14%',
    TARIFA_IVA_15: '15%',
    TARIFA_IVA_NO_OBJETO: 'No objeto de IVA',
    TARIFA_IVA_EXENTO: 'Exento',
}

# ===========================================================================
#  CÓDIGO PORCENTAJE IVA (para reportes SRI)
# ===========================================================================
PCT_IVA_0 = '0'
PCT_IVA_12 = '2'
PCT_IVA_14 = '3'
PCT_IVA_15 = '4'
PCT_IVA_NO_OBJETO = '6'
PCT_IVA_EXENTO = '7'

CODIGOS_PORCENTAJE_IVA = {
    PCT_IVA_0: 0,
    PCT_IVA_12: 12,
    PCT_IVA_14: 14,
    PCT_IVA_15: 15,
    PCT_IVA_NO_OBJETO: 0,
    PCT_IVA_EXENTO: 0,
}

# ===========================================================================
#  CÓDIGO PORCENTAJE ICE (Impuesto a los Consumos Especiales)
# ===========================================================================
ICE_NO_APLICA = '0'
ICE_PORCENTAJES = {
    ICE_NO_APLICA: 'No aplica',
    '1': '2%',
    '2': '5%',
    '3': '10%',
    '4': '15%',
    '5': '20%',
    '6': '30%',
    '7': '50%',
    '8': '70%',
    '9': '100%',
    '10': '150%',
    '11': '300%',
}

# ===========================================================================
#  FORMA DE PAGO (SRI)
# ===========================================================================
PAGO_SIN_UTILIZACION = '01'       # Sin utilización del sistema financiero
PAGO_COMPENSACION = '15'          # Compensación de deudas
PAGO_TARJETA_CREDITO = '19'      # Tarjeta de crédito
PAGO_TARJETA_DEBITO = '20'       # Tarjeta de débito
PAGO_DINERO_ELECTRONICO = '21'   # Dinero electrónico
PAGO_OTROS = '22'                # Otros con utilización del sistema financiero

FORMAS_PAGO_SRI = {
    PAGO_SIN_UTILIZACION: 'Efectivo',
    PAGO_COMPENSACION: 'Compensación',
    PAGO_TARJETA_CREDITO: 'Tarjeta de Crédito',
    PAGO_TARJETA_DEBITO: 'Tarjeta de Débito',
    PAGO_DINERO_ELECTRONICO: 'Dinero Electrónico',
    PAGO_OTROS: 'Otros',
}

# Mapeo de formas de pago del sistema a SRI
MAPEO_FORMAS_PAGO = {
    'EFECTIVO': PAGO_SIN_UTILIZACION,
    'TARJETA_CREDITO': PAGO_TARJETA_CREDITO,
    'TARJETA_DEBITO': PAGO_TARJETA_DEBITO,
    'TRANSFERENCIA': PAGO_OTROS,
    'CHEQUE': PAGO_SIN_UTILIZACION,
    'OTRO': PAGO_OTROS,
}

# ===========================================================================
#  TIPO DE IDENTIFICACIÓN DEL SUJETO RETENIDO
# ===========================================================================
TIPOS_ID_RETENCION = {
    ID_RUC: 'RUC',
    ID_CEDULA: 'Cédula',
    ID_PASAPORTE: 'Pasaporte',
}

# ===========================================================================
#  IMPUESTOS PARA RETENCIONES
# ===========================================================================
IMP_RENTA = '1'       # Impuesto a la Renta
IMP_IVA = '2'         # IVA
IMP_ICE = '3'         # ICE
IMP_ISD = '5'         # Impuesto a la Salida de Divisas

IMPUESTOS_RETENCION = {
    IMP_RENTA: 'Impuesto a la Renta',
    IMP_IVA: 'IVA',
    IMP_ICE: 'ICE',
    IMP_ISD: 'ISD',
}

# ===========================================================================
#  TIPO DE PRODUCTO / SERVICIO
# ===========================================================================
PROD_SERVICIO = 'Servicio'
PROD_PRODUCTO = 'Producto'
PROD_AMBOS = 'Ambos'

# ===========================================================================
#  TIPO DE PRECIO
# ===========================================================================
PRECIO_UNITARIO = 'PRECIO_UNITARIO'
PRECIO_TOTAL = 'PRECIO_TOTAL'
