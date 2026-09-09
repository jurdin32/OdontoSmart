import time
import logging
from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.utils import timezone

from .models import BackgroundTaskLog, ConfiguracionEmpresa, Empresa
from .tasks import (
    enviar_recordatorios_citas,
    generar_facturacion_mensual,
    respaldar_base_datos,
    limpiar_locks_expirados,
)
from core.decorators import permiso_requerido

logger = logging.getLogger(__name__)


def is_admin(user):
    return user.is_authenticated and (
        user.is_superuser or
        (hasattr(user, 'profile') and user.profile.rol and
         user.profile.rol.nombre == 'ADMIN')
    )


@login_required
@user_passes_test(is_admin)
def tareas_list(request):
    """Lista de tareas ejecutadas y botones para ejecutar nuevas."""
    logs = BackgroundTaskLog.objects.all()[:50]
    context = {
        'logs': logs,
        'title': 'Tareas en Segundo Plano',
    }
    return render(request, 'core/tareas.html', context)


@login_required
@user_passes_test(is_admin)
def ejecutar_tarea(request, tarea):
    """Ejecuta una tarea específica de forma sincrónica (para pruebas)."""

    tareas_map = {
        'recordatorios': ('RECORDATORIO_CITAS', enviar_recordatorios_citas),
        'facturacion': ('FACTURACION_MENSUAL',
                       lambda: generar_facturacion_mensual(
                           date.today().month, date.today().year)),
        'respaldo': ('RESPALDO_DB', respaldar_base_datos),
        'limpieza': ('LIMPIEZA_LOCKS', limpiar_locks_expirados),
    }

    if tarea not in tareas_map:
        messages.error(request, f'Tarea "{tarea}" no encontrada.')
        return redirect('tareas_list')

    codigo, fn = tareas_map[tarea]

    # Registrar inicio
    log = BackgroundTaskLog.objects.create(
        tarea=codigo,
        estado='EN_PROCESO',
        detalle='Iniciando...',
        ejecutado_por=request.user,
    )

    inicio = time.time()
    try:
        resultado = fn()
        duracion = time.time() - inicio
        log.estado = 'COMPLETADO'
        log.detalle = str(resultado) if resultado else 'Completado exitosamente'
        log.duracion_segundos = round(duracion, 2)
        log.save()
        messages.success(
            request,
            f'✅ {log.get_tarea_display()} completada en {duracion:.1f}s'
        )
    except Exception as e:
        duracion = time.time() - inicio
        log.estado = 'ERROR'
        log.detalle = str(e)
        log.duracion_segundos = round(duracion, 2)
        log.save()
        messages.error(request, f'❌ {log.get_tarea_display()} falló: {e}')
        logger.exception(f'Error ejecutando tarea {tarea}')

    return redirect('tareas_list')


@login_required
@user_passes_test(is_admin)
def eliminar_log(request, log_id):
    """Elimina un registro de tarea."""
    log = get_object_or_404(BackgroundTaskLog, id=log_id)
    if request.method == 'POST':
        log.delete()
        messages.success(request, 'Registro eliminado.')
    return redirect('tareas_list')


@login_required
@permiso_requerido('ver_configuracion')
def configuracion_empresa(request):
    """Vista de configuración de la empresa actual."""
    from core.tenant import get_empresa
    empresa = get_empresa(request)

    if not empresa:
        messages.error(request, 'No se encontró la empresa.')
        return redirect('dashboard')

    config, created = ConfiguracionEmpresa.objects.get_or_create(empresa=empresa)

    if request.method == 'POST':
        # Verificar permiso de edición
        from core.tenant import tiene_permiso
        if not tiene_permiso(request.user, 'editar_configuracion', empresa):
            messages.error(request, 'No tienes permiso para editar la configuración.')
            return redirect('configuracion_empresa')
        # Resetear colores por defecto
        if 'reset_colores' in request.POST:
            config.color_principal = '#2563eb'
            config.color_secundario = '#1e40af'
            config.save()
            messages.success(request, 'Colores restablecidos a los valores por defecto (azul).')
            return redirect('configuracion_empresa')

        empresa.nombre = request.POST.get('nombre', empresa.nombre)
        empresa.ruc = request.POST.get('ruc', empresa.ruc)
        empresa.direccion = request.POST.get('direccion', empresa.direccion)
        empresa.telefono = request.POST.get('telefono', empresa.telefono)
        empresa.email = request.POST.get('email', empresa.email)
        empresa.save()

        config.color_principal = request.POST.get('color_principal', config.color_principal)
        config.color_secundario = request.POST.get('color_secundario', config.color_secundario)
        config.frase_pie = request.POST.get('frase_pie', config.frase_pie)
        config.moneda = request.POST.get('moneda', config.moneda)

        if 'logo' in request.FILES:
            config.logo = request.FILES['logo']

        config.save()
        messages.success(request, 'Configuración actualizada exitosamente.')
        return redirect('configuracion_empresa')

    context = {
        'empresa': empresa,
        'config': config,
        'title': 'Configuración',
        'active': 'configuracion',
        'default_primary': '#2563eb',
        'default_secondary': '#1e40af',
    }
    return render(request, 'core/configuracion.html', context)
