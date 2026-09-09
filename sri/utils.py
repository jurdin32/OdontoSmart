"""
Utilidades para facturación electrónica SRI Ecuador.
"""

import hashlib
import base64
from datetime import datetime


def generar_clave_acceso(
    ruc: str,
    tipo_documento: str,
    serie: str,
    secuencial: str,
    fecha_emision: datetime,
    ambiente: str,
    codigo_numerico: str = None,
    tipo_emision: str = '1',
) -> str:
    """
    Genera la clave de acceso de 49 dígitos según especificación SRI.

    Composición:
    [01-08] Fecha (ddmmaaaa)
    [09-10] Tipo de comprobante (01=Factura, 04=NC, etc.)
    [11-23] RUC (13 dígitos)
    [24-24] Ambiente (1=Pruebas, 2=Producción)
    [25-27] Establecimiento
    [28-30] Punto de emisión
    [31-39] Secuencial (9 dígitos)
    [40-47] Código numérico (8 dígitos aleatorios)
    [48-48] Tipo de emisión (1=Normal, 2=Indisponibilidad)
    [49-49] Dígito verificador (módulo 11)
    """
    import random
    if codigo_numerico is None:
        codigo_numerico = str(random.randint(0, 99999999)).zfill(8)

    fecha = fecha_emision.strftime('%d%m%Y')
    estab = serie[:3].zfill(3)
    punto_emi = serie[4:7].zfill(3) if '-' in serie else '001'
    sec = str(secuencial).zfill(9)

    # Construir cadena base: 48 dígitos
    base = (
        f"{fecha}{tipo_documento}"
        f"{ruc}{ambiente}"
        f"{estab}{punto_emi}"
        f"{sec}{codigo_numerico}{tipo_emision}"
    )

    # Aplicar módulo 11 para el dígito 49
    digito_verificador = _modulo11(base)

    clave = f"{base}{digito_verificador}"
    return clave


def _modulo11(cadena: str) -> str:
    """
    Algoritmo de dígito verificador módulo 11 usado por el SRI.
    """
    factores = [2, 3, 4, 5, 6, 7]
    total = 0
    pos = len(cadena) - 1

    for char in cadena:
        factor = factores[pos % 6]
        total += int(char) * factor
        pos -= 1

    residuo = total % 11
    digito = 11 - residuo

    if digito == 11:
        return '0'
    elif digito == 10:
        return '1'
    return str(digito)


def serializar_numero(estab: str, punto_emi: str, secuencial: str) -> str:
    """
    Formatea el número de documento: 001-001-000000001
    """
    return f"{estab.zfill(3)}-{punto_emi.zfill(3)}-{str(secuencial).zfill(9)}"


def get_identificacion_tipo(identificacion: str) -> str:
    """
    Determina el tipo de identificación SRI según el número.
    """
    from .enums import ID_RUC, ID_CEDULA, ID_PASAPORTE, ID_CONSUMIDOR_FINAL

    if not identificacion:
        return ID_CONSUMIDOR_FINAL
    id_clean = identificacion.strip()
    if len(id_clean) == 13:
        return ID_RUC
    elif len(id_clean) == 10:
        return ID_CEDULA
    else:
        return ID_PASAPORTE


def get_codigo_porcentaje_iva(porcentaje: float) -> str:
    """
    Obtiene el código SRI para el porcentaje de IVA.
    """
    from .enums import PCT_IVA_0, PCT_IVA_12, PCT_IVA_14, PCT_IVA_15

    if porcentaje == 0:
        return PCT_IVA_0
    elif porcentaje == 12:
        return PCT_IVA_12
    elif porcentaje == 14:
        return PCT_IVA_14
    elif porcentaje == 15:
        return PCT_IVA_15
    return PCT_IVA_0


def get_tarifa_iva(porcentaje: float) -> str:
    """
    Obtiene el código de tarifa IVA SRI.
    """
    from .enums import TARIFA_IVA_0, TARIFA_IVA_12, TARIFA_IVA_14, TARIFA_IVA_15

    if porcentaje == 0:
        return TARIFA_IVA_0
    elif porcentaje == 12:
        return TARIFA_IVA_12
    elif porcentaje == 14:
        return TARIFA_IVA_14
    elif porcentaje == 15:
        return TARIFA_IVA_15
    return TARIFA_IVA_0


def encode_base64(content: bytes) -> str:
    """Codifica contenido a base64."""
    return base64.b64encode(content).decode('utf-8')


def sha256_hex(content: str) -> str:
    """Calcula SHA-256 en hexadecimal."""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()
