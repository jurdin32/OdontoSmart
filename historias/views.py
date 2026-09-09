from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from .models import HistoriaClinica, Evolucion, Odontograma
from .forms import HistoriaClinicaForm, EvolucionForm
from .odontograma_forms import OdontogramaForm
from pacientes.models import Paciente
from medicos.models import Medico
from citas.models import Cita
from usuarios.models import ActivityLog
from django.utils import timezone
import json
from core.concurrency import (
    ConcurrentUpdateError, acquire_lock, release_lock,
    is_locked_by_other, get_locker_user
)
from core.decorators import permiso_requerido


@login_required
@permiso_requerido('ver_historia')
def historia_view(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    historia, created = HistoriaClinica.objects.get_or_create(
        paciente=paciente,
        defaults={'registrado_por': request.user}
    )

    # Solo advertir si otro usuario tiene un lock activo (no adquirir en GET)
    if is_locked_by_other('HistoriaClinica', historia.id, request.user):
        locker = get_locker_user('HistoriaClinica', historia.id)
        messages.warning(
            request,
            f'⚠️ Esta historia clínica está siendo editada por {locker}.'
        )

    if request.method == 'POST':
        version_form = request.POST.get('object_version')
        if version_form:
            historia.version = int(version_form)

        form = HistoriaClinicaForm(request.POST, instance=historia)
        if form.is_valid():
            try:
                form.save()
                ActivityLog.objects.create(
                    usuario=request.user, accion='EDITAR',
                    modelo='HistoriaClínica', objeto_id=historia.id,
                    descripcion=f'Historia de {paciente} actualizada'
                )
                messages.success(request, 'Historia clínica actualizada.')
                release_lock('HistoriaClinica', historia.id, request.user)
                return redirect('historia', paciente_id=paciente.id)
            except ConcurrentUpdateError as e:
                messages.error(request, str(e))
                historia.refresh_from_db()
                form = HistoriaClinicaForm(instance=historia)
        else:
            messages.error(request, 'Por favor corrige los errores.')
    else:
        form = HistoriaClinicaForm(instance=historia)

    evoluciones = historia.evoluciones.select_related('medico').all()

    return render(request, 'historias/historia.html', {
        'form': form, 'paciente': paciente, 'historia': historia,
        'evoluciones': evoluciones, 'created': created,
        'medicos': Medico.objects.filter(activo=True),
        'object_version': historia.version,
        'title': f'Historia - {paciente}'
    })


@login_required
@permiso_requerido('crear_evolucion')
def nueva_evolucion(request, paciente_id):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    historia, _ = HistoriaClinica.objects.get_or_create(
        paciente=paciente,
        defaults={'registrado_por': request.user}
    )

    if request.method == 'POST':
        form = EvolucionForm(request.POST)
        if form.is_valid():
            evol = form.save(commit=False)
            evol.historia = historia
            evol.registrado_por = request.user
            try:
                evol.save()
            except ConcurrentUpdateError as e:
                messages.error(request, str(e))
                return redirect('historia', paciente_id=paciente.id)
            # Auto-generar cita si hay próxima consulta
            if evol.proxima_consulta:
                Cita.objects.create(
                    paciente=paciente,
                    fecha=evol.proxima_consulta,
                    hora=timezone.localtime().time(),
                    motivo=evol.proxima_consulta_nota or 'Control / Seguimiento',
                    estado='PENDIENTE',
                    registrado_por=request.user,
                )
                messages.info(request, f'Cita generada para el {evol.proxima_consulta}.')
            ActivityLog.objects.create(
                usuario=request.user, accion='CREAR',
                modelo='Evolución', objeto_id=evol.id,
                descripcion=f'Evolución registrada para {paciente}'
            )
            messages.success(request, 'Evolución registrada.')
            return redirect('historia', paciente_id=paciente.id)
    else:
        form = EvolucionForm(initial={'fecha': timezone.localdate()})

    return render(request, 'historias/evolucion_form.html', {
        'form': form, 'paciente': paciente, 'title': 'Nueva Evolución'
    })


@login_required
@permiso_requerido('editar_evolucion')
def editar_evolucion(request, evolucion_id):
    evol = get_object_or_404(Evolucion, id=evolucion_id)

    # Bloqueo pesimista
    if is_locked_by_other('Evolucion', evolucion_id, request.user):
        locker = get_locker_user('Evolucion', evolucion_id)
        messages.warning(
            request,
            f'⚠️ Esta evolución está siendo editada por {locker}.'
        )

    # NOTA: El lock se adquiere vía JavaScript al empezar a editar
    if request.method == 'POST':
        version_form = request.POST.get('object_version')
        if version_form:
            evol.version = int(version_form)

        form = EvolucionForm(request.POST, instance=evol)
        if form.is_valid():
            try:
                evol = form.save()
                release_lock('Evolucion', evolucion_id, request.user)
            except ConcurrentUpdateError as e:
                messages.error(request, str(e))
                evol.refresh_from_db()
                form = EvolucionForm(instance=evol)
                return render(request, 'historias/evolucion_form.html', {
                    'form': form, 'paciente': evol.historia.paciente,
                    'evolucion': evol, 'object_version': evol.version,
                    'title': 'Editar Evolución'
                })
            # Auto-generar cita si hay nueva próxima consulta
            if evol.proxima_consulta:
                cita_existente = Cita.objects.filter(
                    paciente=evol.historia.paciente,
                    fecha=evol.proxima_consulta
                ).first()
                if not cita_existente:
                    Cita.objects.create(
                        paciente=evol.historia.paciente,
                        fecha=evol.proxima_consulta,
                        hora=timezone.localtime().time(),
                        motivo=evol.proxima_consulta_nota or 'Control / Seguimiento',
                        estado='PENDIENTE',
                        registrado_por=request.user,
                    )
                    messages.info(request, f'Cita generada para el {evol.proxima_consulta}.')
            messages.success(request, 'Evolución actualizada.')
            return redirect('historia', paciente_id=evol.historia.paciente.id)
    else:
        form = EvolucionForm(instance=evol)
    return render(request, 'historias/evolucion_form.html', {
        'form': form, 'paciente': evol.historia.paciente, 'evolucion': evol,
        'object_version': evol.version,
        'title': 'Editar Evolución'
    })


@login_required
@permiso_requerido('eliminar_evolucion')
def eliminar_evolucion(request, evolucion_id):
    evol = get_object_or_404(Evolucion, id=evolucion_id)
    paciente_id = evol.historia.paciente.id
    if request.method == 'POST':
        evol.delete()
        messages.success(request, 'Evolución eliminada.')
        return redirect('historia', paciente_id=paciente_id)
    return redirect('historia', paciente_id=paciente_id)


@login_required
@permiso_requerido('imprimir_consentimiento')
def imprimir_consentimiento(request, evolucion_id):
    evol = get_object_or_404(Evolucion, id=evolucion_id)
    paciente = evol.historia.paciente
    from datetime import datetime
    MESES = ['enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre']
    fecha_consulta = evol.fecha
    lugar_fecha = f'Cuenca, {fecha_consulta.day} de {MESES[fecha_consulta.month - 1]} del {fecha_consulta.year}'
    return render(request, 'historias/consentimiento_print.html', {
        'evolucion': evol, 'paciente': paciente,
        'lugar_fecha': lugar_fecha,
        'title': f'Consentimiento - {paciente}'
    })


@login_required
@permiso_requerido('ver_odontograma')
def odontograma_view(request, paciente_id, tipo='adulto'):
    paciente = get_object_or_404(Paciente, id=paciente_id)
    historia, _ = HistoriaClinica.objects.get_or_create(
        paciente=paciente, defaults={'registrado_por': request.user}
    )
    odonto, created = Odontograma.objects.get_or_create(historia=historia)

    # Bloqueo pesimista para el odontograma
    if is_locked_by_other('Odontograma', odonto.id, request.user):
        locker = get_locker_user('Odontograma', odonto.id)
        messages.warning(
            request,
            f'⚠️ Este odontograma está siendo editado por {locker}.'
        )

    # NOTA: El lock se adquiere vía JavaScript al empezar a editar
    if request.method == 'POST':
        version_form = request.POST.get('object_version')
        if version_form:
            odonto.version = int(version_form)

        dientes_raw = request.POST.get('dientes', '{}')
        prestaciones_raw = request.POST.get('prestaciones', '{}')
        try:
            odonto.dientes = json.loads(dientes_raw)
        except (json.JSONDecodeError, TypeError):
            pass
        try:
            odonto.prestaciones = json.loads(prestaciones_raw)
        except (json.JSONDecodeError, TypeError):
            pass
        try:
            odonto.save(update_fields=['dientes', 'prestaciones', 'version'])
        except ConcurrentUpdateError as e:
            messages.error(request, str(e))
            odonto.refresh_from_db()
            form = OdontogramaForm(instance=odonto)
            return _render_odontograma(request, paciente, odonto, form, tipo)

        form = OdontogramaForm(request.POST, instance=odonto)
        if form.is_valid():
            try:
                form.save()
                release_lock('Odontograma', odonto.id, request.user)
                messages.success(request, 'Odontograma guardado.')
            except ConcurrentUpdateError as e:
                messages.error(request, str(e))
                odonto.refresh_from_db()
                form = OdontogramaForm(instance=odonto)
                return _render_odontograma(request, paciente, odonto, form, tipo)
        else:
            messages.error(request, 'Corrige los errores del formulario.')
        redirect_url = 'odontograma_infantil' if tipo == 'infantil' else 'odontograma'
        return redirect(redirect_url, paciente_id=paciente.id)
    else:
        form = OdontogramaForm(instance=odonto)

    context = {
        'form': form, 'paciente': paciente,
        'odontograma': odonto,
        'dientes_json': json.dumps(odonto.dientes),
        'prestaciones_json': json.dumps(odonto.prestaciones),
        'superficies': ['vestibular','mesial','distal','lingual','oclusal'],
        'tipo': tipo,
        'object_version': odonto.version,
        'title': f'Odontograma - {paciente}',
    }

    if tipo == 'infantil':
        dientes_sup = ['55','54','53','52','51','61','62','63','64','65']
        dientes_inf = ['85','84','83','82','81','71','72','73','74','75']
        context.update({
            'dientes_sup': dientes_sup,
            'dientes_inf': dientes_inf,
            'es_infantil': True,
        })
        context['title'] = f'Odontograma Infantil - {paciente}'
    else:
        dientes_sup = ['18','17','16','15','14','13','12','11','21','22','23','24','25','26','27','28']
        dientes_inf = ['48','47','46','45','44','43','42','41','31','32','33','34','35','36','37','38']
        context.update({
            'dientes_sup': dientes_sup,
            'dientes_inf': dientes_inf,
            'es_infantil': False,
        })

    context['dientes_visibles'] = dientes_sup + dientes_inf
    return render(request, 'historias/odontograma.html', context)


@login_required
@permiso_requerido('ver_odontograma')
def odontograma_infantil_view(request, paciente_id):
    return odontograma_view(request, paciente_id, tipo='infantil')


def _render_odontograma(request, paciente, odonto, form, tipo):
    """Helper para renderizar odontograma (usado tras error de concurrencia)."""
    dientes_json = json.dumps(odonto.dientes)
    prestaciones_json = json.dumps(odonto.prestaciones)
    context = {
        'form': form, 'paciente': paciente,
        'odontograma': odonto,
        'dientes_json': dientes_json,
        'prestaciones_json': prestaciones_json,
        'superficies': ['vestibular','mesial','distal','lingual','oclusal'],
        'tipo': tipo,
        'object_version': odonto.version,
        'title': f'Odontograma - {paciente}',
    }
    if tipo == 'infantil':
        dientes_sup = ['55','54','53','52','51','61','62','63','64','65']
        dientes_inf = ['85','84','83','82','81','71','72','73','74','75']
        context.update({
            'dientes_sup': dientes_sup, 'dientes_inf': dientes_inf,
            'es_infantil': True,
        })
        context['title'] = f'Odontograma Infantil - {paciente}'
    else:
        dientes_sup = ['18','17','16','15','14','13','12','11','21','22','23','24','25','26','27','28']
        dientes_inf = ['48','47','46','45','44','43','42','41','31','32','33','34','35','36','37','38']
        context.update({
            'dientes_sup': dientes_sup, 'dientes_inf': dientes_inf,
            'es_infantil': False,
        })
    context['dientes_visibles'] = dientes_sup + dientes_inf
    return render(request, 'historias/odontograma.html', context)
