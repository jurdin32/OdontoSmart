from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Medico
from .forms import MedicoForm
from usuarios.models import ActivityLog
from core.decorators import permiso_requerido


@login_required
@permiso_requerido('crear_medicos')
def registrar_medico(request):
    if request.method == 'POST':
        form = MedicoForm(request.POST)
        if form.is_valid():
            medico = form.save()
            ActivityLog.objects.create(
                usuario=request.user, accion='CREAR',
                modelo='Médico', objeto_id=medico.id,
                descripcion=f'Médico Dr. {medico.nombres} {medico.apellidos} registrado'
            )
            messages.success(request, f'Dr. {medico.nombres} {medico.apellidos} registrado.')
            return redirect('lista_medicos')
        else:
            messages.error(request, 'Corrige los errores del formulario.')
    else:
        form = MedicoForm()
    return render(request, 'medicos/registrar.html', {
        'form': form, 'title': 'Registrar Médico'
    })


@login_required
@permiso_requerido('ver_medicos')
def lista_medicos(request):
    q = request.GET.get('q', '').strip()
    medicos = Medico.objects.filter(activo=True)

    if q:
        medicos = medicos.filter(
            Q(nombres__icontains=q) |
            Q(apellidos__icontains=q) |
            Q(cedula__icontains=q) |
            Q(especialidad__icontains=q)
        )

    medicos = medicos.order_by('nombres')
    paginator = Paginator(medicos, 10)
    page = request.GET.get('page', 1)
    medicos_page = paginator.get_page(page)

    return render(request, 'medicos/lista.html', {
        'medicos': medicos_page, 'query': q, 'title': 'Médicos'
    })


@login_required
@permiso_requerido('ver_detalle_medico')
def detalle_medico(request, medico_id):
    medico = get_object_or_404(Medico, id=medico_id)
    return render(request, 'medicos/detalle.html', {
        'medico': medico, 'title': f'Dr. {medico.nombres} {medico.apellidos}'
    })


@login_required
@permiso_requerido('editar_medicos')
def editar_medico(request, medico_id):
    medico = get_object_or_404(Medico, id=medico_id)
    if request.method == 'POST':
        form = MedicoForm(request.POST, instance=medico)
        if form.is_valid():
            form.save()
            ActivityLog.objects.create(
                usuario=request.user, accion='EDITAR',
                modelo='Médico', objeto_id=medico.id,
                descripcion=f'Médico Dr. {medico.nombres} {medico.apellidos} actualizado'
            )
            messages.success(request, 'Médico actualizado.')
            return redirect('lista_medicos')
    else:
        form = MedicoForm(instance=medico)
    return render(request, 'medicos/registrar.html', {
        'form': form, 'medico': medico,
        'title': f'Editar Dr. {medico.nombres} {medico.apellidos}'
    })


@login_required
@permiso_requerido('eliminar_medicos')
def eliminar_medico(request, medico_id):
    medico = get_object_or_404(Medico, id=medico_id)
    if request.method == 'POST':
        nombre = f'{medico.nombres} {medico.apellidos}'
        ActivityLog.objects.create(
            usuario=request.user, accion='ELIMINAR',
            modelo='Médico',
            descripcion=f'Médico Dr. {nombre} eliminado'
        )
        medico.delete()
        messages.success(request, f'Médico {nombre} eliminado.')
        return redirect('lista_medicos')
    return redirect('lista_medicos')
