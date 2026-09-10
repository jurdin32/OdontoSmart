import json
from datetime import date, timedelta

import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator

from .models import (
    MODELOS_SRI_FACTURA, Proforma, Factura, Servicio, generar_numero,
)
from .forms import ProformaForm, FacturaForm, ServicioForm
from pacientes.models import Paciente
from medicos.models import Medico
from usuarios.models import ActivityLog
from core.decorators import permiso_requerido


def _get_empresa(request):
    """Obtiene la empresa desde el request (helper central en core.tenant)."""
    from core.tenant import get_empresa
    return get_empresa(request)


def _get_sri_info(empresa):
    """Obtiene información SRI (ambiente y días restantes del certificado) para mostrar en vistas."""
    from sri.models import SriEmpresaConfig
    from datetime import timezone as dt_tz
    from datetime import datetime

    info = {
        'sri_configurado': False,
        'sri_ambiente': None,
        'sri_ambiente_nombre': None,
        'sri_certificado_valido': False,
        'sri_certificado_dias': None,
        'sri_certificado_titular': None,
        'sri_certificado_hasta': None,
    }

    config = SriEmpresaConfig.objects.filter(empresa=empresa, activo=True).first()
    if not config:
        return info

    info['sri_configurado'] = True
    info['sri_ambiente'] = config.ambiente
    info['sri_ambiente_nombre'] = 'Pruebas' if config.ambiente == '1' else 'Producción'

    if not config.certificado_p12 or not config.clave_certificado:
        return info

    try:
        from cryptography.hazmat.primitives.serialization import pkcs12
        p12_data = config.certificado_p12.read()
        _, cert, _ = pkcs12.load_key_and_certificates(
            p12_data, config.clave_certificado.encode()
        )

        if cert is None:
            return info

        now = datetime.now(dt_tz.utc)
        if cert.not_valid_after_utc >= now and cert.not_valid_before_utc <= now:
            info['sri_certificado_valido'] = True
            info['sri_certificado_dias'] = (cert.not_valid_after_utc - now).days
            info['sri_certificado_hasta'] = cert.not_valid_after_utc.strftime('%d/%m/%Y')

            # Extraer nombre del titular del Subject
            for attr in cert.subject:
                if attr.oid._name == 'commonName':
                    info['sri_certificado_titular'] = attr.value
                    break
    except Exception:
        pass  # Si falla la lectura, solo omitimos los datos del certificado

    return info


# ===========================================================================
#  PROFORMAS
# ===========================================================================

@login_required
@permiso_requerido('ver_proformas')
def lista_proformas(request):
    """Lista todas las proformas de la empresa."""
    empresa = _get_empresa(request)
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '')

    proformas = Proforma.objects.filter(empresa=empresa).select_related('paciente', 'medico')

    if q:
        proformas = proformas.filter(
            Q(numero__icontains=q) |
            Q(paciente__nombres__icontains=q) |
            Q(paciente__apellidos__icontains=q)
        )
    if estado:
        proformas = proformas.filter(estado=estado)

    context = {
        'title': 'Proformas',
        'proformas': proformas,
        'query': q,
        'estado_activo': estado,
        'active': 'proformas',
    }
    return render(request, 'facturacion/proformas_lista.html', context)


@login_required
@permiso_requerido('crear_proformas')
def crear_proforma(request):
    """Crea una nueva proforma."""
    empresa = _get_empresa(request)

    if request.method == 'POST':
        form = ProformaForm(request.POST)
        if form.is_valid():
            proforma = form.save(commit=False)
            proforma.empresa = empresa
            proforma.numero = generar_numero('proforma', empresa.id if empresa else None)
            proforma.registrado_por = request.user
            items_raw = request.POST.get('items', '[]')
            try:
                proforma.items = json.loads(items_raw)
            except (json.JSONDecodeError, TypeError):
                proforma.items = []
            proforma.save()

            ActivityLog.objects.create(
                empresa=empresa, usuario=request.user,
                accion='CREAR', modelo='Proforma',
                objeto_id=proforma.id,
                descripcion=f'Proforma {proforma.numero} creada para {proforma.paciente}'
            )
            messages.success(request, f'Proforma {proforma.numero} creada exitosamente.')
            return redirect('detalle_proforma', proforma_id=proforma.id)
        else:
            messages.error(request, 'Corrige los errores del formulario.')
    else:
        form = ProformaForm()

    items_json = '[]'
    if request.method == 'POST':
        items_json = request.POST.get('items', '[]')

    context = {
        'title': 'Nueva Proforma',
        'form': form,
        'active': 'proformas',
        'items_json': items_json,
        'servicios': Servicio.objects.filter(empresa=empresa, activo=True) if empresa else Servicio.objects.none(),
    }
    return render(request, 'facturacion/proforma_form.html', context)


@login_required
@permiso_requerido('ver_proformas')
def detalle_proforma(request, proforma_id):
    """Muestra el detalle de una proforma."""
    proforma = get_object_or_404(
        Proforma.objects.select_related('paciente', 'medico', 'registrado_por'),
        id=proforma_id
    )
    context = {
        'title': f'Proforma {proforma.numero}',
        'proforma': proforma,
        'active': 'proformas',
    }
    return render(request, 'facturacion/proforma_detalle.html', context)


@login_required
@permiso_requerido('editar_proformas')
def editar_proforma(request, proforma_id):
    """Edita una proforma existente."""
    empresa = _get_empresa(request)
    proforma = get_object_or_404(Proforma, id=proforma_id, empresa=empresa)

    if request.method == 'POST':
        form = ProformaForm(request.POST, instance=proforma)
        if form.is_valid():
            proforma = form.save(commit=False)
            items_raw = request.POST.get('items', '[]')
            try:
                proforma.items = json.loads(items_raw)
            except (json.JSONDecodeError, TypeError):
                pass
            proforma.save()

            ActivityLog.objects.create(
                empresa=empresa, usuario=request.user,
                accion='EDITAR', modelo='Proforma',
                objeto_id=proforma.id,
                descripcion=f'Proforma {proforma.numero} actualizada'
            )
            messages.success(request, f'Proforma {proforma.numero} actualizada.')
            return redirect('detalle_proforma', proforma_id=proforma.id)
        else:
            messages.error(request, 'Corrige los errores.')
    else:
        form = ProformaForm(instance=proforma)

    items_json = None
    if request.method == 'POST':
        items_json = request.POST.get('items', '[]')

    context = {
        'title': f'Editar {proforma.numero}',
        'form': form,
        'proforma': proforma,
        'active': 'proformas',
        'items_json': items_json,
        'servicios': Servicio.objects.filter(empresa=empresa, activo=True) if empresa else Servicio.objects.none(),
    }
    return render(request, 'facturacion/proforma_form.html', context)


@login_required
@permiso_requerido('eliminar_proformas')
def eliminar_proforma(request, proforma_id):
    """Elimina una proforma."""
    empresa = _get_empresa(request)
    proforma = get_object_or_404(Proforma, id=proforma_id, empresa=empresa)
    if request.method == 'POST':
        num = proforma.numero
        proforma.delete()
        messages.success(request, f'Proforma {num} eliminada.')
    return redirect('lista_proformas')


@login_required
@permiso_requerido('crear_facturas')
def proforma_a_factura(request, proforma_id):
    """Convierte una proforma aprobada en factura."""
    empresa = _get_empresa(request)
    proforma = get_object_or_404(Proforma, id=proforma_id, empresa=empresa)

    if proforma.estado not in ('APROBADA', 'PENDIENTE'):
        messages.error(request, 'Solo se pueden facturar proformas pendientes o aprobadas.')
        return redirect('detalle_proforma', proforma_id=proforma.id)

    factura = Factura.objects.create(
        empresa=empresa,
        numero=generar_numero('factura', empresa.id if empresa else None),
        proforma=proforma,
        paciente=proforma.paciente,
        medico=proforma.medico,
        items=proforma.items,
        subtotal=proforma.subtotal,
        descuento_porcentaje=proforma.descuento_porcentaje,
        descuento_monto=proforma.descuento_monto,
        impuesto_porcentaje=proforma.impuesto_porcentaje,
        impuesto_monto=proforma.impuesto_monto,
        total=proforma.total,
        registrado_por=request.user,
    )

    proforma.estado = 'FACTURADA'
    proforma.save()

    ActivityLog.objects.create(
        empresa=empresa, usuario=request.user,
        accion='CREAR', modelo='Factura',
        objeto_id=factura.id,
        descripcion=f'Factura {factura.numero} creada desde proforma {proforma.numero}'
    )
    messages.success(request, f'Factura {factura.numero} creada desde proforma {proforma.numero}.')
    return redirect('detalle_factura', factura_id=factura.id)


@login_required
@permiso_requerido('ver_proformas')
def imprimir_proforma(request, proforma_id):
    """Vista para imprimir una proforma."""
    proforma = get_object_or_404(
        Proforma.objects.select_related('paciente', 'medico', 'registrado_por'),
        id=proforma_id
    )
    context = {
        'title': f'Imprimir {proforma.numero}',
        'proforma': proforma,
    }
    return render(request, 'facturacion/proforma_print.html', context)


# ===========================================================================
#  FACTURAS
# ===========================================================================

@login_required
@permiso_requerido('ver_facturas')
def lista_facturas(request):
    """Lista todas las facturas de la empresa, incluyendo la respuesta del SRI."""
    from sri.models import SriDocumento

    empresa = _get_empresa(request)
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '')
    sri = request.GET.get('sri', '').strip()

    facturas = Factura.objects.filter(empresa=empresa).select_related('paciente', 'medico')

    if q:
        facturas = facturas.filter(
            Q(numero__icontains=q) |
            Q(paciente__nombres__icontains=q) |
            Q(paciente__apellidos__icontains=q)
        )
    if estado:
        facturas = facturas.filter(estado=estado)

    # --- Filtro por estado del SRI ---
    docs = SriDocumento.objects.filter(
        factura_origen_modelo__in=MODELOS_SRI_FACTURA
    )
    if sri:
        con_doc = docs.values_list('factura_origen_id', flat=True)
        if sri == 'AUTORIZADO':
            facturas = facturas.filter(
                id__in=docs.filter(estado='AUTORIZADO')
                .values_list('factura_origen_id', flat=True)
            )
        elif sri == 'PROCESO':
            facturas = facturas.filter(
                id__in=docs.filter(estado__in=['PENDIENTE', 'ENVIADO'])
                .values_list('factura_origen_id', flat=True)
            )
        elif sri == 'RECHAZADO':
            facturas = facturas.filter(
                id__in=docs.filter(estado__in=['NO_AUTORIZADO', 'ERROR'])
                .values_list('factura_origen_id', flat=True)
            )
        elif sri == 'SIN_ENVIAR':
            facturas = facturas.exclude(id__in=con_doc)

    # --- Documento SRI más reciente por factura (1 sola consulta) ---
    facturas = list(facturas)
    documentos = (
        SriDocumento.objects
        .filter(
            factura_origen_modelo__in=MODELOS_SRI_FACTURA,
            factura_origen_id__in=[f.id for f in facturas],
        )
        .order_by('created_at', 'id')
    )
    ultimo_doc = {}
    for doc in documentos:
        ultimo_doc[doc.factura_origen_id] = doc
    for factura in facturas:
        factura.set_sri_documento(ultimo_doc.get(factura.id))

    context = {
        'title': 'Facturas',
        'facturas': facturas,
        'query': q,
        'estado_activo': estado,
        'sri_activo': sri,
        'active': 'facturas',
        'sri_info': _get_sri_info(empresa),
    }
    return render(request, 'facturacion/facturas_lista.html', context)


@login_required
@permiso_requerido('crear_facturas')
def crear_factura(request):
    """Crea una nueva factura directamente (sin proforma)."""
    empresa = _get_empresa(request)

    if request.method == 'POST':
        form = FacturaForm(request.POST)
        if form.is_valid():
            factura = form.save(commit=False)
            factura.empresa = empresa
            factura.numero = generar_numero('factura', empresa.id if empresa else None)
            factura.registrado_por = request.user
            items_raw = request.POST.get('items', '[]')
            try:
                factura.items = json.loads(items_raw)
            except (json.JSONDecodeError, TypeError):
                factura.items = []
            factura.save()

            ActivityLog.objects.create(
                empresa=empresa, usuario=request.user,
                accion='CREAR', modelo='Factura',
                objeto_id=factura.id,
                descripcion=f'Factura {factura.numero} creada para {factura.paciente}'
            )
            messages.success(request, f'Factura {factura.numero} creada exitosamente.')
            return redirect('detalle_factura', factura_id=factura.id)
        else:
            messages.error(request, 'Corrige los errores del formulario.')
    else:
        form = FacturaForm()

    items_json = '[]'
    if request.method == 'POST':
        items_json = request.POST.get('items', '[]')

    context = {
        'title': 'Nueva Factura',
        'form': form,
        'active': 'facturas',
        'items_json': items_json,
        'servicios': Servicio.objects.filter(empresa=empresa, activo=True) if empresa else Servicio.objects.none(),
    }
    return render(request, 'facturacion/factura_form.html', context)


@login_required
@permiso_requerido('ver_facturas')
def detalle_factura(request, factura_id):
    """Muestra el detalle de una factura."""
    factura = get_object_or_404(
        Factura.objects.select_related('paciente', 'medico', 'proforma', 'registrado_por'),
        id=factura_id
    )
    from sri.models import SriDocumento
    import json
    
    # Buscar el documento más reciente para mostrar info
    sri_doc = SriDocumento.objects.filter(
        factura_origen_id=factura.id,
        factura_origen_modelo__in=MODELOS_SRI_FACTURA,
    ).order_by('-created_at').first()
    
    # Buscar documento en ERROR (o ENVIADO con mensajes de error) para reintento
    sri_doc_error = SriDocumento.objects.filter(
        factura_origen_id=factura.id,
        factura_origen_modelo__in=MODELOS_SRI_FACTURA,
        estado__in=['ERROR', 'ENVIADO'],
    ).order_by('-created_at').first()
    # Si el más reciente es ENVIADO pero no tiene errores, ignorarlo
    if sri_doc_error and sri_doc_error.estado == 'ENVIADO':
        msgs = sri_doc_error.mensajes or []
        if not any(m.get('tipo') == 'ERROR' for m in msgs):
            sri_doc_error = None

    # Consultar estado real al SRI si no esta en estado final
    sri_json = None
    if sri_doc and sri_doc.estado not in ('AUTORIZADO',):
        try:
            from sri.services import autorizar_comprobante
            resultado = autorizar_comprobante(
                sri_doc.clave_acceso,
                ambiente=sri_doc.ambiente or '1',
            )
            estado_sri = resultado.get('estado', 'ERROR')
            # Si el SRI dice AUTORIZADO, actualizar el documento
            if estado_sri == 'AUTORIZADO':
                sri_doc.estado = 'AUTORIZADO'
                sri_doc.numero_autorizacion = sri_doc.clave_acceso
                sri_doc.xml_autorizado = resultado.get('xml_autorizado', '')
                if sri_doc.xml_autorizado:
                    from django.core.files.base import ContentFile
                    filename_aut = f'sri_autorizado_{sri_doc.numero_documento.replace("-", "_")}.xml'
                    sri_doc.archivo_xml_autorizado.save(
                        filename_aut, ContentFile(sri_doc.xml_autorizado.encode('utf-8'))
                    )
                sri_doc.save()
            # Guardar los mensajes del SRI como JSON
            mensajes_sri = resultado.get('mensajes', [])
            sri_doc.mensajes = mensajes_sri
            sri_doc.save(update_fields=['mensajes'])
            if mensajes_sri:
                sri_json = json.dumps(mensajes_sri, indent=2, ensure_ascii=False)
        except Exception:
            pass

    if not sri_json and sri_doc and sri_doc.mensajes:
        sri_json = json.dumps(sri_doc.mensajes, indent=2, ensure_ascii=False)

    context = {
        'title': f'Factura {factura.numero}',
        'factura': factura,
        'sri_doc': sri_doc,
        'sri_doc_error': sri_doc_error,
        'sri_json': sri_json,
        'sri_info': _get_sri_info(factura.empresa),
        'active': 'facturas',
    }
    return render(request, 'facturacion/factura_detalle.html', context)


@login_required
@permiso_requerido('editar_facturas')
def editar_factura(request, factura_id):
    """Edita una factura existente."""
    empresa = _get_empresa(request)
    factura = get_object_or_404(Factura, id=factura_id, empresa=empresa)

    if request.method == 'POST':
        form = FacturaForm(request.POST, instance=factura)
        if form.is_valid():
            factura = form.save(commit=False)
            items_raw = request.POST.get('items', '[]')
            try:
                factura.items = json.loads(items_raw)
            except (json.JSONDecodeError, TypeError):
                pass
            factura.save()

            ActivityLog.objects.create(
                empresa=empresa, usuario=request.user,
                accion='EDITAR', modelo='Factura',
                objeto_id=factura.id,
                descripcion=f'Factura {factura.numero} actualizada'
            )
            messages.success(request, f'Factura {factura.numero} actualizada.')
            return redirect('detalle_factura', factura_id=factura.id)
        else:
            messages.error(request, 'Corrige los errores.')
    else:
        form = FacturaForm(instance=factura)

    items_json = None
    if request.method == 'POST':
        items_json = request.POST.get('items', '[]')

    context = {
        'title': f'Editar {factura.numero}',
        'form': form,
        'factura': factura,
        'active': 'facturas',
        'items_json': items_json,
        'servicios': Servicio.objects.filter(empresa=empresa, activo=True) if empresa else Servicio.objects.none(),
    }
    return render(request, 'facturacion/factura_form.html', context)


@login_required
@permiso_requerido('eliminar_facturas')
def eliminar_factura(request, factura_id):
    """Elimina una factura."""
    empresa = _get_empresa(request)
    factura = get_object_or_404(Factura, id=factura_id, empresa=empresa)
    if request.method == 'POST':
        num = factura.numero
        factura.delete()
        messages.success(request, f'Factura {num} eliminada.')
    return redirect('lista_facturas')


@login_required
@permiso_requerido('editar_facturas')
def registrar_pago(request, factura_id):
    """Registra el pago de una factura."""
    empresa = _get_empresa(request)
    factura = get_object_or_404(Factura, id=factura_id, empresa=empresa)

    if request.method == 'POST':
        factura.estado = 'PAGADA'
        factura.fecha_pago = date.today()
        factura.forma_pago = request.POST.get('forma_pago', factura.forma_pago)
        factura.save()

        ActivityLog.objects.create(
            empresa=empresa, usuario=request.user,
            accion='EDITAR', modelo='Factura',
            objeto_id=factura.id,
            descripcion=f'Pago registrado para factura {factura.numero}'
        )
        messages.success(request, f'Pago registrado para factura {factura.numero}.')
    return redirect('detalle_factura', factura_id=factura.id)


@login_required
@permiso_requerido('ver_facturas')
def imprimir_factura(request, factura_id):
    """Vista para imprimir una factura."""
    factura = get_object_or_404(
        Factura.objects.select_related('paciente', 'medico', 'registrado_por'),
        id=factura_id
    )
    context = {
        'title': f'Imprimir {factura.numero}',
        'factura': factura,
    }
    return render(request, 'facturacion/factura_print.html', context)


# ===========================================================================
#  SERVICIOS (Catálogo de tratamientos)
# ===========================================================================

@login_required
@permiso_requerido('ver_servicios')
def lista_servicios(request):
    """Lista los servicios del catálogo de la empresa actual."""
    q = request.GET.get('q', '').strip()
    empresa = _get_empresa(request)
    if not empresa:
        messages.error(request, 'No se encontró la empresa.')
        return redirect('dashboard')

    servicios = Servicio.objects.filter(empresa=empresa)
    if q:
        servicios = servicios.filter(
            Q(nombre__icontains=q) | Q(descripcion__icontains=q)
        )
    servicios = servicios.order_by('-activo', 'nombre')

    paginator = Paginator(servicios, 12)
    page = request.GET.get('page', 1)
    servicios_page = paginator.get_page(page)

    context = {
        'title': 'Servicios',
        'servicios': servicios_page,
        'query': q,
        'total': Servicio.objects.filter(empresa=empresa).count(),
        'total_activos': Servicio.objects.filter(empresa=empresa, activo=True).count(),
        'active': 'servicios',
    }
    return render(request, 'facturacion/servicios_lista.html', context)


@login_required
@permiso_requerido('crear_servicios')
def crear_servicio(request):
    """Crea un nuevo servicio en el catálogo de la empresa."""
    empresa = _get_empresa(request)
    if not empresa:
        messages.error(request, 'No se encontró la empresa.')
        return redirect('dashboard')

    if request.method == 'POST':
        form = ServicioForm(request.POST)
        if form.is_valid():
            servicio = form.save(commit=False)
            servicio.empresa = empresa
            servicio.save()
            ActivityLog.objects.create(
                empresa=empresa, usuario=request.user, accion='CREAR',
                modelo='Servicio', objeto_id=servicio.id,
                descripcion=f'Servicio creado: {servicio.nombre}'
            )
            messages.success(request, f'Servicio "{servicio.nombre}" creado exitosamente.')
            return redirect('lista_servicios')
        messages.error(request, 'Corrige los errores del formulario.')
    else:
        form = ServicioForm()

    return render(request, 'facturacion/servicio_form.html', {
        'title': 'Nuevo Servicio',
        'form': form,
        'active': 'servicios',
    })


@login_required
@permiso_requerido('editar_servicios')
def editar_servicio(request, servicio_id):
    """Edita un servicio existente del catálogo."""
    empresa = _get_empresa(request)
    if not empresa:
        messages.error(request, 'No se encontró la empresa.')
        return redirect('dashboard')
    servicio = get_object_or_404(Servicio, id=servicio_id, empresa=empresa)

    if request.method == 'POST':
        form = ServicioForm(request.POST, instance=servicio)
        if form.is_valid():
            servicio = form.save()
            ActivityLog.objects.create(
                empresa=empresa, usuario=request.user, accion='EDITAR',
                modelo='Servicio', objeto_id=servicio.id,
                descripcion=f'Servicio editado: {servicio.nombre}'
            )
            messages.success(request, f'Servicio "{servicio.nombre}" actualizado.')
            return redirect('lista_servicios')
        messages.error(request, 'Corrige los errores del formulario.')
    else:
        form = ServicioForm(instance=servicio)

    return render(request, 'facturacion/servicio_form.html', {
        'title': f'Editar {servicio.nombre}',
        'form': form,
        'servicio': servicio,
        'active': 'servicios',
    })


@login_required
@permiso_requerido('editar_servicios')
def toggle_servicio(request, servicio_id):
    """Activa o desactiva un servicio (POST)."""
    empresa = _get_empresa(request)
    servicio = get_object_or_404(Servicio, id=servicio_id, empresa=empresa)
    if request.method == 'POST':
        servicio.activo = not servicio.activo
        servicio.save()
        estado = 'activado' if servicio.activo else 'desactivado'
        messages.success(request, f'Servicio "{servicio.nombre}" {estado}.')
    return redirect('lista_servicios')


@login_required
@permiso_requerido('eliminar_servicios')
def eliminar_servicio(request, servicio_id):
    """Elimina un servicio del catálogo (POST)."""
    empresa = _get_empresa(request)
    servicio = get_object_or_404(Servicio, id=servicio_id, empresa=empresa)
    if request.method == 'POST':
        nombre = servicio.nombre
        servicio.delete()
        ActivityLog.objects.create(
            empresa=empresa, usuario=request.user, accion='ELIMINAR',
            modelo='Servicio',
            descripcion=f'Servicio eliminado: {nombre}'
        )
        messages.success(request, f'Servicio "{nombre}" eliminado.')
    return redirect('lista_servicios')
