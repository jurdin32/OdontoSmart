from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Cita
from .forms import CitaForm
from usuarios.models import ActivityLog
from django.utils import timezone
from core.concurrency import (
    ConcurrentUpdateError, acquire_lock, release_lock,
    is_locked_by_other, get_locker_user
)
from core.decorators import permiso_requerido


@login_required
@permiso_requerido('crear_citas')
def registrar_cita(request):
    """Vista para registrar una nueva cita (FBV)"""
    if request.method == 'POST':
        form = CitaForm(request.POST)
        if form.is_valid():
            cita = form.save(commit=False)
            cita.registrado_por = request.user
            cita.save()
            ActivityLog.objects.create(
                usuario=request.user,
                accion='CREAR',
                modelo='Cita',
                objeto_id=cita.id,
                descripcion=f'Cita para {cita.paciente} el {cita.fecha}'
            )
            messages.success(request, 'Cita registrada exitosamente.')
            return redirect('detalle_cita', cita_id=cita.id)
        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        form = CitaForm()

    context = {
        'form': form,
        'title': 'Registrar Cita',
    }
    return render(request, 'citas/registrar.html', context)


@login_required
@permiso_requerido('ver_citas')
def lista_citas(request):
    """Vista para listar todas las citas"""
    q = request.GET.get('q', '').strip()
    estado = request.GET.get('estado', '')
    citas = Cita.objects.all().select_related('paciente', 'doctor')

    if q:
        citas = citas.filter(
            Q(paciente__nombres__icontains=q) |
            Q(paciente__apellidos__icontains=q) |
            Q(paciente__cedula__icontains=q) |
            Q(motivo__icontains=q)
        )

    if estado:
        citas = citas.filter(estado=estado)

    citas = citas.order_by('-fecha', '-hora')
    paginator = Paginator(citas, 10)
    page = request.GET.get('page', 1)
    citas_page = paginator.get_page(page)

    # Conteos para los filtros
    total = Cita.objects.count()
    conteo_pendientes = Cita.objects.filter(estado='PENDIENTE').count()
    conteo_confirmadas = Cita.objects.filter(estado='CONFIRMADA').count()
    conteo_completadas = Cita.objects.filter(estado='COMPLETADA').count()
    conteo_canceladas = Cita.objects.filter(estado='CANCELADA').count()

    context = {
        'citas': citas_page,
        'query': q,
        'estado_activo': estado,
        'conteos': {
            'TODAS': total,
            'PENDIENTE': conteo_pendientes,
            'CONFIRMADA': conteo_confirmadas,
            'COMPLETADA': conteo_completadas,
            'CANCELADA': conteo_canceladas,
        },
        'title': 'Lista de Citas',
    }
    return render(request, 'citas/lista.html', context)


@login_required
@permiso_requerido('ver_detalle_cita')
def detalle_cita(request, cita_id):
    """Vista para ver detalle de una cita"""
    cita = get_object_or_404(Cita.objects.select_related(
        'paciente', 'doctor', 'registrado_por'
    ), id=cita_id)

    context = {
        'cita': cita,
        'title': f'Cita - {cita.paciente}',
    }
    return render(request, 'citas/detalle.html', context)


@login_required
@permiso_requerido('editar_citas')
def editar_cita(request, cita_id):
    """Vista para editar una cita con control de concurrencia."""
    cita = get_object_or_404(Cita, id=cita_id)

    # Bloqueo pesimista
    if is_locked_by_other('Cita', cita_id, request.user):
        locker = get_locker_user('Cita', cita_id)
        messages.warning(
            request,
            f'⚠️ Esta cita está siendo editada por {locker}. '
            'Tus cambios podrían sobrescribirse.'
        )

    # NOTA: El lock se adquiere vía JavaScript solo cuando el usuario
    # comienza a editar el formulario, no al cargar la página.
    if request.method == 'POST':
        version_form = request.POST.get('object_version')
        if version_form:
            cita.version = int(version_form)

        form = CitaForm(request.POST, instance=cita)
        if form.is_valid():
            try:
                form.save()
                ActivityLog.objects.create(
                    usuario=request.user,
                    accion='EDITAR',
                    modelo='Cita',
                    objeto_id=cita.id,
                    descripcion=f'Cita de {cita.paciente} actualizada'
                )
                messages.success(request, 'Cita actualizada exitosamente.')
                release_lock('Cita', cita_id, request.user)
                return redirect('detalle_cita', cita_id=cita.id)
            except ConcurrentUpdateError as e:
                messages.error(request, str(e))
                cita.refresh_from_db()
                form = CitaForm(instance=cita)
        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        form = CitaForm(instance=cita)

    context = {
        'form': form,
        'cita': cita,
        'object_version': cita.version,
        'title': f'Editar Cita - {cita.paciente}',
    }
    return render(request, 'citas/registrar.html', context)


@login_required
@permiso_requerido('eliminar_citas')
def eliminar_cita(request, cita_id):
    """Vista para eliminar una cita (FBV)"""
    cita = get_object_or_404(Cita, id=cita_id)

    if request.method == 'POST':
        ActivityLog.objects.create(
            usuario=request.user,
            accion='ELIMINAR',
            modelo='Cita',
            descripcion=f'Cita de {cita.paciente} eliminada'
        )
        cita.delete()
        messages.success(request, 'Cita eliminada correctamente.')
        return redirect('lista_citas')

    return redirect('lista_citas')


@login_required
@permiso_requerido('cambiar_estado_cita')
def cambiar_estado_cita(request, cita_id):
    """Vista para cambiar el estado de una cita (FBV)"""
    cita = get_object_or_404(Cita, id=cita_id)

    if request.method == 'POST':
        nuevo_estado = request.POST.get('estado')
        if nuevo_estado in dict(Cita.ESTADO_CHOICES):
            cita.estado = nuevo_estado
            try:
                cita.save()
                ActivityLog.objects.create(
                    usuario=request.user,
                    accion='EDITAR',
                    modelo='Cita',
                    objeto_id=cita.id,
                    descripcion=f'Cita de {cita.paciente} cambiada a {cita.get_estado_display()}'
                )
                messages.success(
                    request,
                    f'Estado cambiado a "{cita.get_estado_display()}"'
                )
            except ConcurrentUpdateError:
                messages.error(request, 'La cita fue modificada por otro usuario. Recarga la página.')
        return redirect('detalle_cita', cita_id=cita.id)

    return redirect('lista_citas')
