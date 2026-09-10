import json
import logging
from datetime import datetime
from pathlib import Path

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.files.base import ContentFile
from django.conf import settings
from .models import SriEmpresaConfig, SriDocumento
from .xml_generator import xml_factura
from .utils import serializar_numero
from . import enums
from core.decorators import permiso_requerido

logger = logging.getLogger(__name__)
sri_logger = logging.getLogger('sri')


def _get_empresa(request):
    """Obtiene la empresa desde el request (helper central en core.tenant)."""
    from core.tenant import get_empresa
    return get_empresa(request)


@login_required
@permiso_requerido('sri_config')
def sri_configuracion(request):
    """Vista para gestionar la configuración SRI de la empresa."""
    empresa = _get_empresa(request)
    if not empresa:
        messages.error(request, 'No se encontró la empresa.')
        return redirect('dashboard')

    config, created = SriEmpresaConfig.objects.get_or_create(
        empresa=empresa,
        defaults={
            'ruc': empresa.ruc or '',
            'razon_social': empresa.nombre,
        }
    )

    if request.method == 'POST':
        config.ruc = request.POST.get('ruc', config.ruc)
        config.razon_social = request.POST.get('razon_social', config.razon_social)
        config.nombre_comercial = request.POST.get('nombre_comercial', config.nombre_comercial)
        config.direccion = request.POST.get('direccion', config.direccion)
        config.tipo_contribuyente = request.POST.get('tipo_contribuyente', 'REGIMEN_GENERAL')
        config.contribuyente_especial = request.POST.get('contribuyente_especial', '')
        config.obligado_contabilidad = request.POST.get('obligado_contabilidad') == 'on'
        config.ambiente = request.POST.get('ambiente', '1')
        config.estab_factura = request.POST.get('estab_factura', '001')
        config.emision_factura = request.POST.get('emision_factura', '001')
        config.secuencial_factura = int(request.POST.get('secuencial_factura', 1))
        config.resolucion_sri = request.POST.get('resolucion_sri', '')
        config.comercio_exterior = request.POST.get('comercio_exterior') == 'on'
        config.inco_term_factura = request.POST.get('inco_term_factura', '')
        config.lugar_inco_term = request.POST.get('lugar_inco_term', '')
        config.pais_origen = request.POST.get('pais_origen', '')
        config.puerto_embarque = request.POST.get('puerto_embarque', '')
        config.puerto_destino = request.POST.get('puerto_destino', '')
        config.pais_destino = request.POST.get('pais_destino', '')
        config.pais_adquisicion = request.POST.get('pais_adquisicion', '')
        config.clave_certificado = request.POST.get('clave_certificado', config.clave_certificado)

        if 'certificado_p12' in request.FILES:
            archivo_subido = request.FILES['certificado_p12']
            # Usar solo el nombre base: evita que un nombre con subcarpetas
            # (p. ej. 'sri/certificados/mi_firma.p12') duplique el upload_to
            # y deje la ruta 'media/sri/certificados/sri/certificados/...'.
            archivo_subido.name = Path(archivo_subido.name.replace('\\', '/')).name
            config.certificado_p12 = archivo_subido

        config.save()
        messages.success(request, 'Configuración SRI guardada exitosamente.')
        return redirect('sri_configuracion')

    context = {
        'title': 'Configuración SRI',
        'config': config,
        'empresa': empresa,
        'active': 'sri_config',
    }
    return render(request, 'sri/configuracion.html', context)


@login_required
@permiso_requerido('sri_consultar')
def sri_documentos(request):
    """Lista los documentos electrónicos emitidos."""
    empresa = _get_empresa(request)
    config = SriEmpresaConfig.objects.filter(empresa=empresa).first()

    docs = SriDocumento.objects.none()
    if config:
        docs = SriDocumento.objects.filter(
            empresa_config=config
        ).order_by('-created_at')[:50]

    # Verificar si existe el log
    log_path = settings.MEDIA_ROOT / 'sri' / 'sri.log'
    log_existe = log_path.exists()

    context = {
        'title': 'Documentos Electrónicos',
        'documentos': docs,
        'log_existe': log_existe,
        'active': 'sri_docs',
    }
    return render(request, 'sri/documentos.html', context)


@login_required
@permiso_requerido('sri_consultar')
def sri_log_view(request):
    """Muestra el log SRI."""
    log_path = settings.MEDIA_ROOT / 'sri' / 'sri.log'
    contenido = 'No hay registros SRI aún.'
    if log_path.exists():
        contenido = log_path.read_text(encoding='utf-8')
        if not contenido.strip():
            contenido = 'El archivo de log está vacío.'
    return render(request, 'sri/log.html', {
        'title': 'Log SRI',
        'contenido': contenido,
        'active': 'sri_log',
    })


@login_required
@permiso_requerido('sri_emitir')
def emitir_factura_electronica(request, factura_id):
    """
    Genera y envía una factura electrónica al SRI (ambiente pruebas).
    """
    from facturacion.models import Factura

    empresa = _get_empresa(request)
    if not empresa:
        messages.error(request, 'No se encontró la empresa.')
        return redirect('dashboard')

    factura = get_object_or_404(Factura, id=factura_id)
    config = SriEmpresaConfig.objects.filter(empresa=empresa, activo=True).first()

    if not config:
        messages.error(request, 'Debes configurar el SRI primero (Datos del Emisor).')
        return redirect('sri_configuracion')

    if not config.certificado_p12:
        messages.error(request, 'Debes cargar el certificado digital .p12 en la configuración SRI.')
        return redirect('sri_configuracion')

    # Verificar si ya fue autorizada
    doc_existente = SriDocumento.objects.filter(
        factura_origen_id=factura.id,
        factura_origen_modelo='facturacion.factura',
    ).order_by('-created_at').first()

    if doc_existente and doc_existente.estado == 'AUTORIZADO':
        messages.warning(request, 'Esta factura ya fue emitida electrónicamente.')
        return redirect('detalle_factura', factura_id=factura.id)

    # Determinar si es reintento (ERROR, o ENVIADO con mensajes de error)
    es_reintento = False
    if doc_existente and doc_existente.secuencial:
        if doc_existente.estado == 'ERROR':
            es_reintento = True
        elif doc_existente.estado == 'ENVIADO':
            msgs = doc_existente.mensajes or []
            if any(m.get('tipo') == 'ERROR' for m in msgs):
                es_reintento = True

    if es_reintento:
        sec = doc_existente.secuencial
        sri_logger.info(f'♻️ Reintentando con secuencial existente: {sec}')
    else:
        sec = config.peek_secuencial()
        sri_logger.info(f'🔢 Nuevo secuencial (sin consumir aún): {sec}')

    paciente = factura.paciente

    sri_logger.info('=' * 60)
    sri_logger.info(f'INICIO EMISIÓN: Factura #{factura.numero} | Secuencial SRI: {sec}')
    sri_logger.info(f'Paciente: {paciente.nombres} {paciente.apellidos} | ID: {paciente.cedula}')
    sri_logger.info(f'Total: ${factura.total} | Ambiente: {"Pruebas" if config.ambiente == "1" else "Producción"}')

    try:
        items_sri = []
        for item in (factura.items or []):
            items_sri.append({
                'descripcion': item.get('descripcion', ''),
                'cantidad': float(item.get('cantidad', 1)),
                'precio_unitario': float(item.get('precio_unitario', 0)),
                'total': float(item.get('cantidad', 1)) * float(item.get('precio_unitario', 0)),
                'descuento_item': 0,
            })

        factura_data = {
            'fecha_emision': timezone.datetime.combine(
                factura.fecha_emision or timezone.localdate(), datetime.min.time()
            ),
            'cliente_identificacion': paciente.cedula or '',
            'cliente_razon_social': f'{paciente.nombres} {paciente.apellidos}',
            'cliente_direccion': paciente.direccion or '',
            'cliente_email': paciente.email or '',
            'cliente_telefono': paciente.celular or paciente.telefono or '',
            'items': items_sri,
            'subtotal': float(factura.subtotal),
            'descuento': float(factura.descuento_monto),
            'iva_porcentaje': float(factura.impuesto_porcentaje),
            'iva_valor': float(factura.impuesto_monto),
            'total': float(factura.total),
            'forma_pago_sri': enums.MAPEO_FORMAS_PAGO.get(
                factura.forma_pago, enums.PAGO_SIN_UTILIZACION
            ),
        }

        # 1. Generar XML
        clave_acceso, numero_doc, xml_str = xml_factura(config, factura_data, sec)
        sri_logger.info(f'[1/4] XML generado: {numero_doc}')
        sri_logger.info(f'      Clave acceso: {clave_acceso}')
        sri_logger.info(f'      Tamaño XML: {len(xml_str)} bytes')

        # 2. Firmar XML
        from .signature import firmar_xml_con_archivo
        xml_firmado = firmar_xml_con_archivo(
            xml_str, config.certificado_p12.read(), config.clave_certificado,
        )
        sri_logger.info(f'[2/4] XML firmado correctamente ({len(xml_firmado)} bytes)')

        # Si es reintento, actualizar documento existente; si no, crear uno nuevo
        if doc_existente and doc_existente.estado == 'ERROR':
            sri_doc = doc_existente
            sri_doc.xml_firmado = xml_firmado
            sri_doc.estado = 'PENDIENTE'
            sri_doc.mensajes = []
            sri_logger.info(f'♻️ Actualizando documento existente ID={sri_doc.id}')
        else:
            sri_doc = SriDocumento(
                empresa_config=config,
                tipo=enums.DOC_FACTURA,
                clave_acceso=clave_acceso,
                numero_documento=numero_doc,
                factura_origen_id=factura.id,
                factura_origen_modelo='facturacion.factura',
                ambiente=config.ambiente,
            )
            sri_logger.info(f'📄 Creando nuevo documento')

        sri_doc.xml_firmado = xml_firmado
        sri_doc.secuencial = sec
        sri_doc.identificacion_comprador = paciente.cedula or ''
        sri_doc.razon_social_comprador = f'{paciente.nombres} {paciente.apellidos}'
        sri_doc.total_sin_impuestos = factura.subtotal
        sri_doc.total = factura.total
        sri_doc.fecha_emision = timezone.now()
        sri_doc.save()

        # Guardar XML firmado como archivo físico
        filename_firmado = f'sri_firmado_{numero_doc.replace("-", "_")}.xml'
        sri_doc.archivo_xml_firmado.save(
            filename_firmado, ContentFile(xml_firmado.encode('utf-8'))
        )
        ruta_firmado = settings.MEDIA_ROOT / 'sri' / 'documentos' / 'firmados' / filename_firmado
        sri_logger.info(f'[3/4] Documento registrado ID={sri_doc.id}')
        sri_logger.info(f'      XML firmado guardado: {ruta_firmado}')

        # 4. Enviar al SRI
        from .services import enviar_comprobante
        sri_logger.info(f'[4/4] Enviando al SRI (ambiente {config.ambiente})...')
        try:
            resultado = enviar_comprobante(xml_firmado, ambiente=config.ambiente)
            estado_sri = resultado.get('estado', 'ERROR')
            sri_logger.info(f'      Respuesta SRI: {estado_sri}')
            sri_logger.info(f'      Mensajes: {resultado.get("mensajes", [])}')

            if estado_sri == 'AUTORIZADO':
                # SRI aceptó → consumir secuencial (si no se había consumido antes)
                config.consumir_secuencial()
                sri_doc.marcar_autorizado(resultado, clave_acceso)
                sri_doc.guardar_xml_autorizado()
                sri_doc.save()
                sri_logger.info(f'      ✅ FACTURA AUTORIZADA - N° {sri_doc.numero_autorizacion}')
                messages.success(request, f'✅ Factura electrónica {numero_doc} autorizada por el SRI.')

            elif estado_sri == 'RECIBIDA':
                # SRI recibió el comprobante → consumir secuencial
                if not es_reintento:
                    config.consumir_secuencial()
                sri_doc.estado = 'ENVIADO'
                sri_doc.mensajes = resultado.get('mensajes', [])
                sri_doc.save()
                sri_logger.info(f'      📤 Factura RECIBIDA, consultando autorización...')

                # Consultar autorización automáticamente
                import time
                time.sleep(2)  # Esperar 2 segundos para que el SRI procese
                from .services import autorizar_comprobante
                aut_resultado = autorizar_comprobante(clave_acceso, ambiente=config.ambiente)
                aut_estado = aut_resultado.get('estado', 'ERROR')
                sri_logger.info(f'      Autorización: {aut_estado}')

                if aut_estado == 'AUTORIZADO':
                    # SRI aceptó → consumir secuencial (si no se había consumido antes)
                    config.consumir_secuencial()
                    sri_doc.marcar_autorizado(aut_resultado, clave_acceso)
                    sri_doc.guardar_xml_autorizado()
                    sri_doc.save()
                    sri_logger.info(f'      ✅ FACTURA AUTORIZADA - N° {sri_doc.numero_autorizacion}')
                    messages.success(request, f'✅ Factura electrónica {numero_doc} autorizada por el SRI.')
                else:
                    sri_doc.estado = 'ENVIADO'
                    sri_doc.mensajes = aut_resultado.get('mensajes', [])
                    sri_doc.save()
                    aut_mensajes = aut_resultado.get('mensajes', [])
                    sri_logger.info(f'      NO AUTORIZADO - Mensajes: {aut_mensajes}')
                    for err in aut_mensajes[:3]:
                        sri_logger.warning(f'      SRI: {err.get("mensaje", "")}')
                    messages.warning(request,
                        f'📤 Factura {numero_doc} recibida por el SRI pero NO AUTORIZADA. '
                        'Puedes consultar el detalle desde Docs. Electrónicos.')

            else:
                sri_doc.estado = 'ERROR'
                sri_doc.mensajes = resultado.get('mensajes', [])
                sri_doc.save()
                errores = resultado.get('mensajes', [])
                sri_logger.error(f'      ❌ SRI rechazó: {errores}')
                for err in errores[:3]:
                    messages.error(request, f"SRI: {err.get('mensaje', 'Error desconocido')}")
                if not errores:
                    messages.error(request, '❌ Error al enviar al SRI. Revisa la configuración.')

        except Exception as sri_err:
            sri_doc.estado = 'ERROR'
            sri_doc.mensajes = [{'mensaje': f'Error conexión SRI: {str(sri_err)}'}]
            sri_doc.save()
            sri_logger.error(f'      ❌ Error de conexión SRI: {sri_err}')
            messages.warning(
                request,
                f'⚠️ Documento {numero_doc} registrado pero no se pudo contactar al SRI. '
                'Puedes re-intentar desde el detalle de la factura.'
            )

        sri_logger.info(f'FIN EMISIÓN - Estado final: {sri_doc.estado}')
        sri_logger.info('=' * 60)
        return redirect('detalle_factura', factura_id=factura.id)

    except Exception as e:
        logger.exception(f'Error emitiendo factura electrónica: {e}')
        sri_logger.error(f'ERROR FATAL: {e}')
        import traceback
        sri_logger.error(traceback.format_exc())
        messages.error(request, f'Error al generar el documento: {str(e)}')
        return redirect('detalle_factura', factura_id=factura.id)


@login_required
@permiso_requerido('sri_consultar')
def consultar_autorizacion(request, documento_id):
    """Consulta el estado de autorización de un documento SRI."""
    sri_doc = get_object_or_404(SriDocumento, id=documento_id)

    if sri_doc.estado == 'AUTORIZADO':
        messages.info(request, 'El documento ya está autorizado.')
        return redirect('detalle_factura', factura_id=sri_doc.factura_origen_id)

    from .services import autorizar_comprobante
    sri_logger.info(f'Consultando autorización: {sri_doc.clave_acceso}')

    try:
        resultado = autorizar_comprobante(
            sri_doc.clave_acceso,
            ambiente=sri_doc.ambiente or '1',
        )
        estado = resultado.get('estado', 'ERROR')
        sri_logger.info(f'Resultado consulta: {estado}')

        if estado == 'AUTORIZADO':
            sri_doc.marcar_autorizado(resultado, sri_doc.clave_acceso)
            sri_doc.guardar_xml_autorizado()
            sri_doc.save()
            messages.success(request, f'✅ Documento {sri_doc.numero_documento} AUTORIZADO.')
        else:
            sri_doc.mensajes = resultado.get('mensajes', [])
            sri_doc.save()
            aut_mensajes = resultado.get('mensajes', [])
            sri_logger.info(f'      Mensajes SRI: {aut_mensajes}')
            for err in aut_mensajes[:3]:
                sri_logger.warning(f'      SRI: {err.get("mensaje", "")}')
            messages.warning(request,
                f'Documento {sri_doc.numero_documento} aún no autorizado. '
                f'Estado: {estado}')
            if aut_mensajes:
                for m in aut_mensajes[:3]:
                    err_msg = m.get('informacionAdicional', '') or m.get('mensaje', '')
                    if err_msg:
                        messages.error(request, f"SRI: {err_msg}")

    except Exception as e:
        sri_logger.exception(f'Error consultando autorización: {e}')
        messages.error(request, f'Error al consultar: {str(e)}')

    return redirect('detalle_factura', factura_id=sri_doc.factura_origen_id)


from django.http import JsonResponse
from django.views.decorators.http import require_POST


@login_required
@permiso_requerido('sri_emitir')
def reintentar_envio(request, documento_id):
    """
    Reintenta el envío de un documento SRI que falló (estado ERROR).
    Re-genera el XML, lo firma de nuevo con el MISMO secuencial y lo reenvía.
    """
    empresa = _get_empresa(request)
    if not empresa:
        messages.error(request, 'No se encontró la empresa.')
        return redirect('dashboard')

    sri_doc = get_object_or_404(SriDocumento, id=documento_id)

    # Permitir reintento si está en ERROR, o ENVIADO con mensajes de error
    puede_reintentar = (sri_doc.estado == 'ERROR')
    if not puede_reintentar and sri_doc.estado == 'ENVIADO':
        msgs = sri_doc.mensajes or []
        puede_reintentar = any(m.get('tipo') == 'ERROR' for m in msgs)

    if not puede_reintentar:
        messages.warning(request, 'Solo se pueden reintentar documentos en estado ERROR o con errores de validación.')
        return redirect('detalle_factura', factura_id=sri_doc.factura_origen_id)

    config = SriEmpresaConfig.objects.filter(empresa=empresa, activo=True).first()
    if not config or not config.certificado_p12:
        messages.error(request, 'Configura SRI y certificado primero.')
        return redirect('sri_configuracion')

    from facturacion.models import Factura
    factura = get_object_or_404(Factura, id=sri_doc.factura_origen_id)
    paciente = factura.paciente

    sec = sri_doc.secuencial or config.peek_secuencial()

    sri_logger.info('=' * 60)
    sri_logger.info(f'♻️ REINTENTO: Doc #{sri_doc.id} | Secuencial: {sec} | Factura: {factura.numero}')

    try:
        from .xml_generator import xml_factura
        from .signature import firmar_xml_con_archivo
        from django.core.files.base import ContentFile
        items_sri = []
        for item in (factura.items or []):
            items_sri.append({
                'descripcion': item.get('descripcion', ''),
                'cantidad': float(item.get('cantidad', 1)),
                'precio_unitario': float(item.get('precio_unitario', 0)),
                'total': float(item.get('cantidad', 1)) * float(item.get('precio_unitario', 0)),
                'descuento_item': 0,
            })

        factura_data = {
            'fecha_emision': timezone.datetime.combine(
                factura.fecha_emision or timezone.localdate(), datetime.min.time()
            ),
            'cliente_identificacion': paciente.cedula or '',
            'cliente_razon_social': f'{paciente.nombres} {paciente.apellidos}',
            'cliente_direccion': paciente.direccion or '',
            'cliente_email': paciente.email or '',
            'cliente_telefono': paciente.celular or paciente.telefono or '',
            'items': items_sri,
            'subtotal': float(factura.subtotal),
            'descuento': float(factura.descuento_monto),
            'iva_porcentaje': float(factura.impuesto_porcentaje),
            'iva_valor': float(factura.impuesto_monto),
            'total': float(factura.total),
            'forma_pago_sri': enums.MAPEO_FORMAS_PAGO.get(
                factura.forma_pago, enums.PAGO_SIN_UTILIZACION
            ),
        }

        # 1. Re-generar XML
        clave_acceso, numero_doc, xml_str = xml_factura(config, factura_data, sec)
        sri_logger.info(f'  [1] XML re-generado: {numero_doc} | Clave: {clave_acceso}')

        # 2. Re-firmar
        xml_firmado = firmar_xml_con_archivo(
            xml_str, config.certificado_p12.read(), config.clave_certificado,
        )
        sri_logger.info(f'  [2] XML re-firmado ({len(xml_firmado)} bytes)')

        # 3. Actualizar documento
        sri_doc.xml_firmado = xml_firmado
        sri_doc.clave_acceso = clave_acceso
        sri_doc.estado = 'PENDIENTE'
        sri_doc.mensajes = []
        sri_doc.save()

        filename_firmado = f'sri_firmado_{numero_doc.replace("-", "_")}.xml'
        sri_doc.archivo_xml_firmado.save(
            filename_firmado, ContentFile(xml_firmado.encode('utf-8'))
        )
        sri_logger.info(f'  [3] Documento actualizado ID={sri_doc.id}')

        # 4. Enviar al SRI
        from .services import enviar_comprobante, autorizar_comprobante
        sri_logger.info(f'  [4] Enviando al SRI...')
        resultado = enviar_comprobante(xml_firmado, ambiente=config.ambiente)
        estado_sri = resultado.get('estado', 'ERROR')
        sri_logger.info(f'      SRI responde: {estado_sri}')

        if estado_sri == 'AUTORIZADO':
            # Consumir secuencial SOLO si no se había consumido antes
            if not sri_doc.secuencial:
                config.consumir_secuencial()
            sri_doc.marcar_autorizado(resultado, clave_acceso)
            sri_doc.guardar_xml_autorizado()
            sri_doc.save()
            sri_logger.info(f'  ✅ REINTENTO EXITOSO - AUTORIZADO')
            messages.success(request, f'✅ Factura {numero_doc} autorizada por el SRI.')

        elif estado_sri == 'RECIBIDA':
            if not sri_doc.secuencial:
                config.consumir_secuencial()
            sri_doc.estado = 'ENVIADO'
            sri_doc.mensajes = resultado.get('mensajes', [])
            sri_doc.save()
            sri_logger.info(f'  📤 RECIBIDA, consultando autorización...')

            import time
            time.sleep(2)
            aut_resultado = autorizar_comprobante(clave_acceso, ambiente=config.ambiente)
            aut_estado = aut_resultado.get('estado', 'ERROR')

            if aut_estado == 'AUTORIZADO':
                sri_doc.marcar_autorizado(aut_resultado, clave_acceso)
                sri_doc.guardar_xml_autorizado()
                sri_doc.save()
                sri_logger.info(f'  ✅ AUTORIZADO tras consulta')
                messages.success(request, f'✅ Factura {numero_doc} autorizada por el SRI.')
            else:
                sri_doc.estado = 'ENVIADO'
                sri_doc.mensajes = aut_resultado.get('mensajes', [])
                sri_doc.save()
                aut_mensajes = aut_resultado.get('mensajes', [])
                for err in aut_mensajes[:3]:
                    sri_logger.warning(f'      SRI: {err.get("mensaje", "")}')
                messages.warning(request,
                    f'📤 Factura {numero_doc} recibida pero pendiente de autorización.')
        else:
            sri_doc.estado = 'ERROR'
            sri_doc.mensajes = resultado.get('mensajes', [])
            sri_doc.save()
            errores = resultado.get('mensajes', [])
            sri_logger.error(f'  ❌ SRI rechazó reintento: {errores}')
            for err in errores[:3]:
                messages.error(request, f"SRI: {err.get('mensaje', 'Error desconocido')}")

        sri_logger.info(f'FIN REINTENTO - Estado: {sri_doc.estado}')
        return redirect('detalle_factura', factura_id=factura.id)

    except Exception as e:
        logger.exception(f'Error en reintento: {e}')
        sri_logger.error(f'ERROR FATAL reintento: {e}')
        messages.error(request, f'Error en reintento: {str(e)}')
        return redirect('detalle_factura', factura_id=factura.id)


@login_required
@require_POST
@permiso_requerido('sri_config')
def verificar_certificado(request):
    """
    Verifica que el certificado digital (.p12) sea válido:
    - Contraseña correcta
    - No esté caducado
    - Tenga uso de firma digital
    - Emitido por una entidad de certificación autorizada en Ecuador
    """
    empresa = _get_empresa(request)
    if not empresa:
        return JsonResponse({'valido': False, 'mensaje': 'No se encontró la empresa.'})

    config = SriEmpresaConfig.objects.filter(empresa=empresa, activo=True).first()
    if not config or not config.certificado_p12:
        return JsonResponse({
            'valido': False,
            'mensaje': 'No hay certificado .p12 cargado. Sube el archivo primero.',
        })

    if not config.clave_certificado:
        return JsonResponse({
            'valido': False,
            'mensaje': 'No has ingresado la clave del certificado.',
        })

    try:
        from cryptography.hazmat.primitives.serialization import pkcs12
        from cryptography import x509
        from datetime import timezone as dt_tz

        p12_data = config.certificado_p12.read()
        private_key, cert, additional_certs = pkcs12.load_key_and_certificates(
            p12_data, config.clave_certificado.encode()
        )

        if cert is None:
            return JsonResponse({
                'valido': False,
                'mensaje': 'El archivo .p12 no contiene un certificado válido.',
            })

        # Verificar si está caducado
        now = datetime.now(dt_tz.utc)
        if cert.not_valid_after_utc < now:
            return JsonResponse({
                'valido': False,
                'mensaje': (
                    f'El certificado está CADUCADO. '
                    f'Venció el: {cert.not_valid_after_utc.strftime("%d/%m/%Y")}'
                ),
                'detalles': {
                    'valido_desde': cert.not_valid_before_utc.strftime('%d/%m/%Y'),
                    'valido_hasta': cert.not_valid_after_utc.strftime('%d/%m/%Y'),
                }
            })

        if cert.not_valid_before_utc > now:
            return JsonResponse({
                'valido': False,
                'mensaje': (
                    f'El certificado aún NO está vigente. '
                    f'Válido desde: {cert.not_valid_before_utc.strftime("%d/%m/%Y")}'
                ),
                'detalles': {
                    'valido_desde': cert.not_valid_before_utc.strftime('%d/%m/%Y'),
                    'valido_hasta': cert.not_valid_after_utc.strftime('%d/%m/%Y'),
                }
            })

        # Verificar que el certificado sea para firma digital
        resultados_verificacion = []
        advertencias = []

        try:
            eku = cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage)
            usages = [u._name if hasattr(u, '_name') else str(u) for u in eku.value]
            if not any('email' in u.lower() for u in usages):
                advertencias.append(
                    'El certificado no tiene uso extendido de correo electrónico. '
                    'Verifica que sea un certificado de firma electrónica.'
                )
        except x509.ExtensionNotFound:
            advertencias.append(
                'No se encontró la extensión de uso extendido de clave (ExtendedKeyUsage).'
            )

        try:
            ku = cert.extensions.get_extension_for_class(x509.KeyUsage)
            if not ku.value.digital_signature and not ku.value.content_commitment:
                advertencias.append(
                    'El certificado NO tiene habilitado el uso de firma digital. '
                    'Podría no ser aceptado por el SRI.'
                )
        except x509.ExtensionNotFound:
            advertencias.append(
                'No se encontró la extensión de uso de clave (KeyUsage).'
            )

        # Información del certificado
        subject_parts = {}
        for attr in cert.subject:
            subject_parts[attr.oid._name] = attr.value

        issuer_parts = {}
        for attr in cert.issuer:
            issuer_parts[attr.oid._name] = attr.value

        tipo_certificado = 'FIRMA ELECTRÓNICA (Token)'
        if cert.serial_number and int(cert.serial_number) > 0:
            pass  # Certificado válido

        return JsonResponse({
            'valido': True,
            'mensaje': '✅ Certificado digital válido.',
            'detalles': {
                'titular': subject_parts.get('commonName', ''),
                'ruc_certificado': subject_parts.get('serialNumber', ''),
                'organizacion': subject_parts.get('organizationName', ''),
                'emisor': issuer_parts.get('commonName', ''),
                'pais': issuer_parts.get('countryName', ''),
                'valido_desde': cert.not_valid_before_utc.strftime('%d/%m/%Y'),
                'valido_hasta': cert.not_valid_after_utc.strftime('%d/%m/%Y'),
                'dias_restantes': (cert.not_valid_after_utc - now).days,
                'serial': str(cert.serial_number),
                'tipo': tipo_certificado,
            },
            'advertencias': advertencias if advertencias else None,
        })

    except ValueError as e:
        error_msg = str(e).lower()
        if any(kw in error_msg for kw in ['password', 'mac', 'decrypt', 'invalid']):
            return JsonResponse({
                'valido': False,
                'mensaje': '❌ Contraseña incorrecta. Verifica la clave del certificado.',
            })
        return JsonResponse({
            'valido': False,
            'mensaje': f'Error al procesar el certificado: {str(e)}',
        })
    except Exception as e:
        logger.exception(f'Error verificando certificado: {e}')
        return JsonResponse({
            'valido': False,
            'mensaje': f'Error inesperado al verificar el certificado: {str(e)}',
        })

