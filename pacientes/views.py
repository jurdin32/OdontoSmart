from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Paciente
from .forms import PacienteForm
from usuarios.models import ActivityLog
from core.concurrency import (
    ConcurrentUpdateError, acquire_lock, release_lock,
    is_locked_by_other, get_locker_user
)
from core.decorators import permiso_requerido
from core.tenant import get_empresa


@login_required
@permiso_requerido('crear_pacientes')
def registrar_paciente(request):
    """Vista para registrar un nuevo paciente (FBV)"""
    if request.method == 'POST':
        form = PacienteForm(request.POST, request.FILES)
        if form.is_valid():
            paciente = form.save(commit=False)
            paciente.empresa = get_empresa(request)
            paciente.registrado_por = request.user
            paciente.save()
            ActivityLog.objects.create(
                empresa=paciente.empresa,
                usuario=request.user,
                accion='CREAR',
                modelo='Paciente',
                objeto_id=paciente.id,
                descripcion=f'Paciente {paciente.nombres} {paciente.apellidos} registrado'
            )
            messages.success(
                request,
                f'Paciente {paciente.nombres} {paciente.apellidos} registrado exitosamente.'
            )
            return redirect('lista_pacientes')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = PacienteForm()

    context = {
        'form': form,
        'title': 'Registrar Paciente',
    }
    return render(request, 'pacientes/registrar.html', context)


@login_required
@permiso_requerido('ver_pacientes')
def lista_pacientes(request):
    """Vista para listar todos los pacientes"""
    q = request.GET.get('q', '').strip()
    empresa = get_empresa(request)
    pacientes = Paciente.objects.filter(
        activo=True, empresa=empresa
    ) if empresa else Paciente.objects.none()

    if q:
        pacientes = pacientes.filter(
            Q(nombres__icontains=q) |
            Q(apellidos__icontains=q) |
            Q(cedula__icontains=q)
        )

    pacientes = pacientes.order_by('-fecha_registro')
    paginator = Paginator(pacientes, 10)
    page = request.GET.get('page', 1)
    pacientes_page = paginator.get_page(page)

    context = {
        'pacientes': pacientes_page,
        'query': q,
        'title': 'Lista de Pacientes',
    }
    return render(request, 'pacientes/lista.html', context)


@login_required
@permiso_requerido('ver_detalle_paciente')
def detalle_paciente(request, paciente_id):
    """Vista para ver detalle de un paciente"""
    paciente = get_object_or_404(
        Paciente, id=paciente_id, empresa=get_empresa(request)
    )

    context = {
        'paciente': paciente,
        'title': f'{paciente.nombres} {paciente.apellidos}',
    }
    return render(request, 'pacientes/detalle.html', context)


@login_required
@permiso_requerido('editar_pacientes')
def editar_paciente(request, paciente_id):
    """Vista para editar un paciente (FBV) con control de concurrencia."""
    paciente = get_object_or_404(
        Paciente, id=paciente_id, empresa=get_empresa(request)
    )

    # ---- Bloqueo pesimista: verificar si otro usuario lo está editando ----
    if is_locked_by_other('Paciente', paciente_id, request.user):
        locker = get_locker_user('Paciente', paciente_id)
        messages.warning(
            request,
            f'⚠️ Este paciente está siendo editado por {locker}. '
            'Tus cambios podrían sobrescribirse.'
        )

    # NOTA: El lock se adquiere vía JavaScript solo cuando el usuario
    # comienza a editar el formulario, no al cargar la página.
    if request.method == 'POST':
        # Restaurar versión desde el formulario oculto
        version_form = request.POST.get('object_version')
        if version_form:
            paciente.version = int(version_form)

        form = PacienteForm(request.POST, request.FILES, instance=paciente)
        if form.is_valid():
            try:
                form.save()
                ActivityLog.objects.create(
                    empresa=paciente.empresa,
                    usuario=request.user,
                    accion='EDITAR',
                    modelo='Paciente',
                    objeto_id=paciente.id,
                    descripcion=f'Paciente {paciente.nombres} {paciente.apellidos} actualizado'
                )
                messages.success(
                    request,
                    f'Paciente {paciente.nombres} {paciente.apellidos} actualizado.'
                )
                release_lock('Paciente', paciente_id, request.user)
                return redirect('detalle_paciente', paciente_id=paciente.id)
            except ConcurrentUpdateError as e:
                messages.error(request, str(e))
                # Refrescar datos del paciente
                paciente.refresh_from_db()
                form = PacienteForm(instance=paciente)
        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        form = PacienteForm(instance=paciente)

    context = {
        'form': form,
        'paciente': paciente,
        'object_version': paciente.version,
        'title': f'Editar {paciente.nombres} {paciente.apellidos}',
    }
    return render(request, 'pacientes/registrar.html', context)


@login_required
@permiso_requerido('eliminar_pacientes')
def eliminar_paciente(request, paciente_id):
    """Vista para eliminar un paciente (FBV) - Solo POST"""
    paciente = get_object_or_404(
        Paciente, id=paciente_id, empresa=get_empresa(request)
    )

    if request.method == 'POST':
        nombre_completo = f'{paciente.nombres} {paciente.apellidos}'
        ActivityLog.objects.create(
            empresa=paciente.empresa,
            usuario=request.user,
            accion='ELIMINAR',
            modelo='Paciente',
            objeto_id=paciente.id,
            descripcion=f'Paciente {nombre_completo} eliminado'
        )
        paciente.delete()
        messages.success(
            request,
            f'Paciente {nombre_completo} eliminado correctamente.'
        )
        return redirect('lista_pacientes')

    return redirect('lista_pacientes')

