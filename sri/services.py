"""
Servicios web SOAP del SRI para facturación electrónica.

Endpoints:
- Pruebas: https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl
- Producción: https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline?wsdl

Procesos:
1. Recepción: Enviar XML firmado al SRI
2. Autorización: Consultar autorización usando clave de acceso
"""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime
from . import enums

logger = logging.getLogger(__name__)


# URLs de los servicios SRI
URLS_SRI = {
    enums.AMBIENTE_PRUEBAS: {
        'recepcion': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline',
        'autorizacion': 'https://celcer.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline',
    },
    enums.AMBIENTE_PRODUCCION: {
        'recepcion': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/RecepcionComprobantesOffline',
        'autorizacion': 'https://cel.sri.gob.ec/comprobantes-electronicos-ws/AutorizacionComprobantesOffline',
    },
}


def enviar_comprobante(xml_firmado: str, ambiente: str = enums.AMBIENTE_PRUEBAS) -> dict:
    """
    Envía un comprobante electrónico firmado al SRI.

    Args:
        xml_firmado: XML del comprobante firmado digitalmente
        ambiente: '1' para pruebas, '2' para producción

    Returns:
        dict: {'estado': 'AUTORIZADO'|'RECIBIDA'|'ERROR',
               'mensajes': [...],
               'numero_autorizacion': '...'}
    """
    import base64
    import requests

    url = URLS_SRI[ambiente]['recepcion']
    xml_base64 = base64.b64encode(xml_firmado.encode('utf-8')).decode('utf-8')

    soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                      xmlns:ec="http://ec.gob.sri.ws.recepcion">
       <soapenv:Header/>
       <soapenv:Body>
          <ec:validarComprobante>
             <xml>{xml_base64}</xml>
          </ec:validarComprobante>
       </soapenv:Body>
    </soapenv:Envelope>"""

    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': '',
        'User-Agent': 'OdontSmart/1.0',
    }

    try:
        response = requests.post(
            url, data=soap_body.encode('utf-8'),
            headers=headers, timeout=60,
            verify=True,
        )
        return _parse_respuesta_recepcion(response.text)
    except requests.exceptions.RequestException as e:
        logger.error(f'Error enviando comprobante al SRI: {e}')
        return {
            'estado': 'ERROR',
            'mensajes': [{'mensaje': f'Error de conexión: {str(e)}'}],
        }


def autorizar_comprobante(clave_acceso: str, ambiente: str = enums.AMBIENTE_PRUEBAS) -> dict:
    """
    Consulta la autorización de un comprobante.

    Args:
        clave_acceso: Clave de acceso de 49 dígitos
        ambiente: '1' pruebas, '2' producción

    Returns:
        dict con estado y datos de autorización
    """
    import requests

    url = URLS_SRI[ambiente]['autorizacion']

    soap_body = f"""<?xml version="1.0" encoding="UTF-8"?>
    <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                      xmlns:ec="http://ec.gob.sri.ws.autorizacion">
       <soapenv:Header/>
       <soapenv:Body>
          <ec:autorizacionComprobante>
             <claveAccesoComprobante>{clave_acceso}</claveAccesoComprobante>
          </ec:autorizacionComprobante>
       </soapenv:Body>
    </soapenv:Envelope>"""

    headers = {
        'Content-Type': 'text/xml; charset=utf-8',
        'SOAPAction': '',
        'User-Agent': 'OdontSmart/1.0',
    }

    try:
        response = requests.post(
            url, data=soap_body.encode('utf-8'),
            headers=headers, timeout=60,
            verify=True,
        )
        return _parse_respuesta_autorizacion(response.text)
    except requests.exceptions.RequestException as e:
        logger.error(f'Error consultando autorización SRI: {e}')
        return {
            'estado': 'ERROR',
            'mensajes': [{'mensaje': f'Error de conexión: {str(e)}'}],
        }


def _parse_respuesta_recepcion(xml_response: str) -> dict:
    """Parsea la respuesta SOAP de recepción del SRI."""
    # Guardar un snippet de la respuesta para diagnóstico
    snippet = xml_response[:500] if xml_response else '(vacía)'
    logger.info(f'Respuesta SRI (primeros 500 chars): {snippet}')

    # Si la respuesta parece HTML (fault de conexión/proxy), mostrarlo
    if xml_response.strip().startswith('<'):
        pass  # es XML
    elif not xml_response.strip():
        return {'estado': 'ERROR', 'mensajes': [{'mensaje': 'Respuesta vacía del SRI'}]}
    else:
        return {
            'estado': 'ERROR',
            'mensajes': [{'mensaje': f'Respuesta no XML del SRI: {snippet[:200]}'}],
        }

    try:
        root = ET.fromstring(xml_response)

        # Intentar con namespace de respuesta SRI estándar
        namespaces_try = [
            {'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
             'ns2': 'http://ec.gob.sri.ws.recepcion'},
            {'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
             'ns2': 'http://ec.gob.sri.ws.recepcion'},
            # Sin namespace (respuesta simplificada)
            {},
        ]

        resp = None
        ns_used = {}
        for ns_try in namespaces_try:
            if ns_try:
                resp = root.find('.//ns2:RespuestaRecepcionComprobante', ns_try)
            else:
                # Buscar sin namespace
                for elem in root.iter():
                    if 'RespuestaRecepcionComprobante' in elem.tag:
                        resp = elem
                        break
            if resp is not None:
                ns_used = ns_try
                break

        if resp is None:
            # Intentar extraer cualquier mensaje de fault SOAP
            fault = root.find('.//{http://schemas.xmlsoap.org/soap/envelope/}Fault')
            if fault is not None:
                fault_str = ET.tostring(fault, encoding='unicode')[:300]
                return {
                    'estado': 'ERROR',
                    'mensajes': [{'mensaje': f'Error SOAP del SRI: {fault_str}'}],
                }
            return {
                'estado': 'ERROR',
                'mensajes': [{'mensaje': f'Respuesta SRI no esperada. Ver logs para detalle. Snippet: {snippet[:200]}'}],
            }

        estado = resp.find('ns2:estado', ns_used) if ns_used else resp.find('estado')
        if estado is None and not ns_used:
            # Sin namespace, buscar por tag local
            for child in resp:
                if 'estado' in child.tag:
                    estado = child
                    break
        estado_text = estado.text if estado is not None else 'ERROR'

        mensajes = []
        # Buscar mensajes en toda la jerarquía (respuesta directa o dentro de comprobantes)
        msg_nodes = []
        if ns_used:
            msg_nodes = resp.findall('.//ns2:mensaje', ns_used)
        else:
            for elem in resp.iter():
                if 'mensaje' in elem.tag and elem.tag.endswith('mensaje'):
                    msg_nodes.append(elem)

        for m in msg_nodes:
            def txt(tag):
                el = m.find(tag) if ns_used else None
                if el is None and not ns_used:
                    for child in m:
                        if tag in child.tag or child.tag.endswith(tag):
                            return child.text or ''
                return el.text if el is not None else ''

            msg = {
                'identificador': txt('identificador'),
                'mensaje': txt('mensaje'),
                'tipo': txt('tipo'),
                'informacionAdicional': txt('informacionAdicional'),
            }
            # Si no se encontró con tag completo, buscar por substring
            if not msg['mensaje'] and not ns_used:
                for child in m:
                    if 'mensaje' in child.tag and child.text:
                        msg['mensaje'] = child.text
            if not msg['identificador'] and not ns_used:
                for child in m:
                    if 'identificador' in child.tag and child.text:
                        msg['identificador'] = child.text
            # Solo agregar si tiene al menos un mensaje
            if msg['mensaje'] or msg['identificador']:
                mensajes.append(msg)

        return {'estado': estado_text, 'mensajes': mensajes}

    except ET.ParseError as e:
        logger.error(f'Error parseando respuesta SRI: {e}')
        return {'estado': 'ERROR', 'mensajes': [{'mensaje': f'Error de parseo: {e}'}]}


def _parse_respuesta_autorizacion(xml_response: str) -> dict:
    """Parsea la respuesta SOAP de autorización del SRI."""
    snippet = xml_response[:500] if xml_response else '(vacía)'
    logger.info(f'Respuesta autorización SRI: {snippet}')

    # Log completo para diagnóstico si hay error
    if 'NO AUTORIZADO' in xml_response or 'ERROR' in xml_response[:1000]:
        logger.info(f'Respuesta autorización COMPLETA: {xml_response[:3000]}')

    try:
        root = ET.fromstring(xml_response)

        # Buscar RespuestaAutorizacionComprobante con y sin namespace
        ns_map = [
            {'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
             'ns2': 'http://ec.gob.sri.ws.autorizacion'},
            {'soap': 'http://schemas.xmlsoap.org/soap/envelope/',
             'ns2': 'http://ec.gob.sri.ws.autorizacion'},
        ]

        resp = None
        ns_used = None
        for ns_try in ns_map:
            resp = root.find('.//ns2:RespuestaAutorizacionComprobante', ns_try)
            if resp is not None:
                ns_used = ns_try
                break

        # Buscar sin namespace
        if resp is None:
            for elem in root.iter():
                if 'RespuestaAutorizacionComprobante' in elem.tag:
                    resp = elem
                    break

        if resp is None:
            # Verificar si hay SOAP Fault
            fault = root.find('.//{http://schemas.xmlsoap.org/soap/envelope/}Fault')
            if fault is not None:
                fault_str = ET.tostring(fault, encoding='unicode')[:300]
                return {'estado': 'ERROR', 'mensajes': [{'mensaje': f'SOAP Fault: {fault_str}'}]}
            return {'estado': 'ERROR', 'mensajes': [{'mensaje': f'Respuesta inesperada: {snippet[:200]}'}]}

        # Buscar autorizaciones dentro de la respuesta
        if ns_used:
            aut = resp.find('.//ns2:autorizacion', ns_used)
        else:
            aut = None
            for elem in resp.iter():
                if 'autorizacion' in elem.tag and elem.tag.endswith('autorizacion'):
                    aut = elem
                    break

        if aut is not None:
            if ns_used:
                num_aut = _get_text(aut, 'ns2:numeroAutorizacion', ns_used)
                fecha_aut = _get_text(aut, 'ns2:fechaAutorizacion', ns_used)
                xml_aut = _get_text(aut, 'ns2:comprobante', ns_used)
                estado_aut = _get_text(aut, 'ns2:estado', ns_used)
            else:
                def find_text(parent, tag):
                    for child in parent:
                        if tag in child.tag:
                            return child.text or ''
                    return ''
                num_aut = find_text(aut, 'numeroAutorizacion')
                fecha_aut = find_text(aut, 'fechaAutorizacion')
                xml_aut = find_text(aut, 'comprobante')
                estado_aut = find_text(aut, 'estado')

            # Extraer mensajes de error del nodo autorización (si existen)
            mensajes_aut = []
            if ns_used:
                msg_nodes = aut.findall('.//ns2:mensaje', ns_used)
                for m in msg_nodes:
                    mensajes_aut.append({
                        'identificador': _get_text(m, 'ns2:identificador', ns_used),
                        'mensaje': _get_text(m, 'ns2:mensaje', ns_used),
                        'tipo': _get_text(m, 'ns2:tipo', ns_used),
                        'informacionAdicional': _get_text(m, 'ns2:informacionAdicional', ns_used),
                    })
            else:
                for elem in aut.iter():
                    if 'mensaje' in elem.tag and elem.tag.endswith('mensaje'):
                        m = elem
                        def _find(parent, tag):
                            for child in parent:
                                if tag in child.tag:
                                    return child.text or ''
                            return ''
                        mensajes_aut.append({
                            'identificador': _find(m, 'identificador'),
                            'mensaje': _find(m, 'mensaje'),
                            'tipo': _find(m, 'tipo'),
                            'informacionAdicional': _find(m, 'informacionAdicional'),
                        })

            if estado_aut == 'AUTORIZADO' or (not estado_aut and num_aut):
                return {
                    'estado': 'AUTORIZADO',
                    'numero_autorizacion': num_aut,
                    'fecha_autorizacion': fecha_aut,
                    'xml_autorizado': xml_aut,
                    'mensajes': mensajes_aut,
                }
            else:
                if not mensajes_aut:
                    mensajes_aut = [{'mensaje': f'Estado: {estado_aut or "NO_AUTORIZADO"}'}]
                return {
                    'estado': estado_aut or 'NO_AUTORIZADO',
                    'numero_autorizacion': num_aut,
                    'fecha_autorizacion': fecha_aut,
                    'xml_autorizado': xml_aut,
                    'mensajes': mensajes_aut,
                }

        # No hay autorización aún, devolver estado de la respuesta
        if ns_used:
            estado = resp.find('ns2:estado', ns_used)
        else:
            estado = None
            for child in resp:
                if 'estado' in child.tag:
                    estado = child
                    break
        estado_text = estado.text if estado is not None else 'ERROR'

        return {
            'estado': estado_text,
            'numero_autorizacion': None,
            'fecha_autorizacion': None,
            'xml_autorizado': None,
            'mensajes': [{'mensaje': f'Sin autorización. Estado: {estado_text}'}],
        }

    except ET.ParseError as e:
        logger.error(f'Error parseando autorización SRI: {e}')
        return {'estado': 'ERROR', 'mensajes': [{'mensaje': f'Error de parseo: {e}'}]}


def _get_text(element, tag, ns):
    """Obtiene texto de un elemento XML."""
    el = element.find(tag, ns)
    return el.text if el is not None else ''
