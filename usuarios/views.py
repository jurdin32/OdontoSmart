from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Q
from .forms import CustomLoginForm, CustomUserCreationForm
from .models import ActivityLog, Role
from pacientes.models import Paciente
from citas.models import Cita
from medicos.models import Medico
from core.decorators import permiso_requerido


def login_view(request):
    """Vista de inicio de sesión con soporte multi-tenant"""
    if request.user.is_authenticated:
        return redirect('dashboard')

    empresa = getattr(request, 'empresa', None)

    if request.method == 'POST':
        form = CustomLoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                # Modo clínica única: garantizamos que el perfil pertenezca a la clínica
                profile = getattr(user, 'profile', None)
                if profile and empresa and profile.empresa_id != empresa.id:
                    profile.empresa = empresa
                    profile.save()
                login(request, user)
                _registrar_login(user)
                return redirect('dashboard')
            else:
                messages.error(request, 'Usuario o contraseña incorrectos.')
        else:
            messages.error(request, 'Por favor corrige los errores del formulario.')
    else:
        form = CustomLoginForm()

    context = {
        'form': form,
        'title': 'Iniciar Sesión',
        'empresa': empresa,
    }
    return render(request, 'registration/login.html', context)


def _registrar_login(user):
    """Registra el inicio de sesión en ActivityLog."""
    empresa_id = user.profile.empresa_id if hasattr(user, 'profile') else None
    ActivityLog.objects.create(
        empresa_id=empresa_id,
        usuario=user,
        accion='LOGIN',
        modelo='Usuario',
        descripcion=f'Inicio de sesión - {user.get_full_name() or user.username}'
    )


def logout_view(request):
    """Vista de cierre de sesión"""
    logout(request)
    messages.info(request, 'Has cerrado sesión correctamente.')
    return redirect('login')


def reset_password_view(request):
    """Vista para restablecer contraseña solo con el nombre de usuario"""
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if not username:
            messages.error(request, 'Debes ingresar tu nombre de usuario.')
        elif not User.objects.filter(username=username).exists():
            messages.error(request, 'No existe un usuario con ese nombre.')
        elif not password1:
            messages.error(request, 'Debes ingresar una nueva contraseña.')
        elif password1 != password2:
            messages.error(request, 'Las contraseñas no coinciden.')
        elif len(password1) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
        else:
            user = User.objects.get(username=username)
            user.set_password(password1)
            user.save()
            messages.success(request, '¡Contraseña restablecida exitosamente! Ahora puedes iniciar sesión.')
            return redirect('login')

    return render(request, 'registration/reset_password.html', {'title': 'Restablecer Contraseña'})


@login_required
def dashboard_view(request):
    """Vista del panel principal después del inicio de sesión"""
    user = request.user
    profile = user.profile
    empresa = getattr(request, 'empresa', None) or getattr(profile, 'empresa', None)
    hoy = timezone.localdate()

    empresa_filter = Q(empresa=empresa) if empresa else Q()

    total_pacientes = Paciente.objects.filter(empresa_filter, activo=True).count()
    citas_hoy = Cita.objects.filter(empresa_filter, fecha=hoy).exclude(estado='CANCELADA').count()
    total_medicos = Medico.objects.filter(empresa_filter, activo=True).count()
    citas_pendientes = Cita.objects.filter(empresa_filter, estado='PENDIENTE').count()

    # Actividad reciente categorizada
    ultimas = ActivityLog.objects.filter(empresa_filter)[:20]
    grupos = {}
    for act in ultimas:
        key = (act.accion, act.modelo)
        if key not in grupos:
            grupos[key] = {'accion': act.accion, 'modelo': act.modelo, 'items': [], 'total': 0}
        if len(grupos[key]['items']) < 2:
            grupos[key]['items'].append(act)
        grupos[key]['total'] += 1

    orden_accion = {'CREAR': 0, 'EDITAR': 1, 'ELIMINAR': 2, 'LOGIN': 3}
    grupos_lista = sorted(grupos.values(), key=lambda g: (
        orden_accion.get(g['accion'], 99), g['modelo']
    ))

    context = {
        'title': 'Panel Principal',
        'user': user,
        'profile': profile,
        'grupos_actividad': grupos_lista,
        'total_pacientes': total_pacientes,
        'citas_hoy': citas_hoy,
        'total_medicos': total_medicos,
        'citas_pendientes': citas_pendientes,
    }
    return render(request, 'dashboard.html', context)


@login_required
def buscar_view(request):
    """Búsqueda global de pacientes filtrada por empresa"""
    q = request.GET.get('q', '').strip()
    empresa = getattr(request, 'empresa', None) or getattr(request.user.profile, 'empresa', None)
    results = []
    if q and empresa:
        pacientes = Paciente.objects.filter(
            Q(empresa=empresa, activo=True) &
            (Q(nombres__icontains=q) |
             Q(apellidos__icontains=q) |
             Q(cedula__icontains=q))
        )[:10]
        for p in pacientes:
            results.append({
                'id': p.id,
                'nombre': f'{p.nombres} {p.apellidos}',
                'cedula': p.cedula,
                'url': f'/pacientes/{p.id}/'
            })
    return JsonResponse({'results': results})


# ===========================================================================
#  GESTIÓN DE USUARIOS (Multi-tenant)
# ===========================================================================

def _get_empresa(request):
    """Obtiene la empresa desde el request (helper central en core.tenant)."""
    from core.tenant import get_empresa
    return get_empresa(request)


@login_required
@permiso_requerido('ver_usuarios')
def lista_usuarios(request):
    """Lista los usuarios de la empresa actual."""
    empresa = _get_empresa(request)
    if not empresa:
        messages.error(request, 'No se encontró la empresa.')
        return redirect('dashboard')

    usuarios = User.objects.filter(
        profile__empresa=empresa
    ).select_related('profile__rol', 'medico').order_by('username')

    # Ver permisos de admin
    es_admin = request.user.is_superuser or (
        hasattr(request.user, 'profile') and
        request.user.profile.rol and
        request.user.profile.rol.nombre == 'ADMIN'
    )

    context = {
        'title': 'Usuarios',
        'usuarios': usuarios,
        'es_admin': es_admin,
        'active': 'usuarios',
    }
    return render(request, 'usuarios/lista.html', context)


@login_required
@permiso_requerido('crear_usuarios')
def registrar_usuario(request):
    """Crea un nuevo usuario en la empresa actual."""
    empresa = _get_empresa(request)
    if not empresa:
        messages.error(request, 'No se encontró la empresa.')
        return redirect('dashboard')

    # Solo admin puede crear usuarios
    es_admin = request.user.is_superuser or (
        hasattr(request.user, 'profile') and
        request.user.profile.rol and
        request.user.profile.rol.nombre == 'ADMIN'
    )
    if not es_admin:
        messages.error(request, 'No tienes permiso para crear usuarios.')
        return redirect('lista_usuarios')

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            # Asignar empresa al perfil
            profile = user.profile
            profile.empresa = empresa
            profile.telefono = form.cleaned_data.get('telefono', '')
            rol_nombre = form.cleaned_data.get('rol')
            if rol_nombre:
                try:
                    profile.rol = Role.objects.get(nombre=rol_nombre)
                except Role.DoesNotExist:
                    pass
            profile.save()

            # Si el rol es DOCTOR, crear o vincular Médico automáticamente
            if rol_nombre == 'DOCTOR':
                _vincular_medico(user, empresa)

            ActivityLog.objects.create(
                empresa=empresa,
                usuario=request.user,
                accion='CREAR',
                modelo='Usuario',
                descripcion=f'Usuario creado: {user.get_full_name() or user.username}'
            )
            messages.success(
                request,
                f'Usuario "{user.get_full_name() or user.username}" creado exitosamente.'
            )
            return redirect('lista_usuarios')
        else:
            messages.error(request, 'Corrige los errores del formulario.')
    else:
        form = CustomUserCreationForm()

    context = {
        'title': 'Registrar Usuario',
        'form': form,
        'active': 'usuarios',
    }
    return render(request, 'usuarios/registrar.html', context)


def _normalizar_nombre_usuario(user):
    """Devuelve nombres y apellidos seguros, incluso si el usuario viene sin datos."""
    nombres = (user.first_name or '').strip()
    apellidos = (user.last_name or '').strip()
    if not nombres and not apellidos:
        return user.username, user.username
    if not nombres:
        nombres = user.username
    if not apellidos:
        apellidos = user.username
    return nombres, apellidos


def _vincular_medico(user, empresa):
    """Busca un médico sin usuario en la misma empresa y lo vincula, o crea uno nuevo."""
    primer_nombre = (user.first_name or '').strip().split()[0] if (user.first_name or '').strip() else ''
    medico = Medico.objects.filter(
        empresa=empresa,
        user__isnull=True,
        activo=True
    ).filter(
        Q(cedula=user.username) | Q(email=user.email) |
        Q(nombres__icontains=primer_nombre)
    ).first()

    if medico:
        medico.user = user
        medico.save()
    else:
        # Crear médico automáticamente con datos del usuario
        nombres, apellidos = _normalizar_nombre_usuario(user)
        Medico.objects.create(
            empresa=empresa,
            user=user,
            nombres=nombres,
            apellidos=apellidos,
            cedula=user.username,
            especialidad='ODONTO_GENERAL',
            registro_profesional=f'TEMP-{user.username}',
            telefono=getattr(user.profile, 'telefono', ''),
            email=user.email,
        )


@login_required
@permiso_requerido('editar_usuarios')
def editar_usuario(request, user_id):
    """Edita un usuario de la empresa."""
    empresa = _get_empresa(request)
    if not empresa:
        messages.error(request, 'No se encontró la empresa.')
        return redirect('dashboard')

    user_edit = get_object_or_404(User, id=user_id, profile__empresa=empresa)
    profile = user_edit.profile

    if request.method == 'POST':
        user_edit.first_name = request.POST.get('first_name', user_edit.first_name)
        user_edit.last_name = request.POST.get('last_name', user_edit.last_name)
        user_edit.email = request.POST.get('email', user_edit.email)
        user_edit.save()

        profile.telefono = request.POST.get('telefono', profile.telefono)
        rol_nombre = request.POST.get('rol')
        if rol_nombre:
            try:
                profile.rol = Role.objects.get(nombre=rol_nombre)
            except Role.DoesNotExist:
                pass
        profile.save()

        # Cambiar contraseña si se envió
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        if password1 and password1 == password2 and len(password1) >= 8:
            user_edit.set_password(password1)
            user_edit.save()

        ActivityLog.objects.create(
            empresa=empresa,
            usuario=request.user,
            accion='EDITAR',
            modelo='Usuario',
            descripcion=f'Usuario editado: {user_edit.get_full_name() or user_edit.username}'
        )
        messages.success(request, 'Usuario actualizado exitosamente.')
        return redirect('lista_usuarios')

    context = {
        'title': 'Editar Usuario',
        'user_edit': user_edit,
        'profile': profile,
        'roles': Role.objects.all(),
        'active': 'usuarios',
    }
    return render(request, 'usuarios/editar.html', context)


@login_required
@permiso_requerido('asignar_permisos')
def asignar_permisos(request, user_id):
    """Asigna permisos a un usuario dentro de la empresa."""
    empresa = _get_empresa(request)
    if not empresa:
        messages.error(request, 'No se encontró la empresa.')
        return redirect('dashboard')

    user_perm = get_object_or_404(User, id=user_id, profile__empresa=empresa)

    if request.method == 'POST':
        # Limpiar permisos actuales y asignar los seleccionados
        from core.models import PermisoUsuario, Permiso
        PermisoUsuario.objects.filter(empresa=empresa, usuario=user_perm).delete()

        codigos = request.POST.getlist('permisos')
        for codigo in codigos:
            try:
                permiso = Permiso.objects.get(codigo=codigo)
                PermisoUsuario.objects.create(
                    empresa=empresa,
                    usuario=user_perm,
                    permiso=permiso
                )
            except Permiso.DoesNotExist:
                pass

        messages.success(
            request,
            f'Permisos actualizados para {user_perm.get_full_name() or user_perm.username}.'
        )
        return redirect('lista_usuarios')

    from core.models import Permiso, PermisoUsuario
    permisos = Permiso.objects.all().order_by('modulo', 'nombre')
    permisos_asignados = PermisoUsuario.objects.filter(
        empresa=empresa, usuario=user_perm
    ).values_list('permiso__codigo', flat=True)

    context = {
        'title': f'Permisos - {user_perm.get_full_name() or user_perm.username}',
        'user_perm': user_perm,
        'permisos': permisos,
        'permisos_asignados': list(permisos_asignados),
        'active': 'usuarios',
    }
    return render(request, 'usuarios/permisos.html', context)


@login_required
def toggle_usuario_activo(request, user_id):
    """Activa/desactiva un usuario (solo admin)."""
    empresa = _get_empresa(request)
    if not empresa:
        messages.error(request, 'No se encontró la empresa.')
        return redirect('dashboard')

    user_toggle = get_object_or_404(User, id=user_id, profile__empresa=empresa)
    if request.method == 'POST':
        user_toggle.is_active = not user_toggle.is_active
        user_toggle.save()
        estado = 'activado' if user_toggle.is_active else 'desactivado'
        messages.success(request, f'Usuario {estado} correctamente.')
    return redirect('lista_usuarios')


# ===========================================================================
#  VINCULAR MÉDICOS EXISTENTES CON USUARIOS
# ===========================================================================

@login_required
def medicos_sin_usuario(request):
    """Lista médicos que aún no tienen usuario vinculado."""
    empresa = _get_empresa(request)
    if not empresa:
        messages.error(request, 'No se encontró la empresa.')
        return redirect('dashboard')

    medicos = Medico.objects.filter(empresa=empresa, user__isnull=True, activo=True)
    context = {
        'title': 'Vincular Médicos',
        'medicos': medicos,
        'active': 'usuarios',
    }
    return render(request, 'usuarios/medicos_sin_usuario.html', context)


@login_required
def crear_usuario_desde_medico(request, medico_id):
    """Crea un usuario a partir de un médico existente."""
    empresa = _get_empresa(request)
    if not empresa:
        messages.error(request, 'No se encontró la empresa.')
        return redirect('dashboard')

    medico = get_object_or_404(Medico, id=medico_id, empresa=empresa, user__isnull=True)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        if not username or not password:
            messages.error(request, 'Debes ingresar usuario y contraseña.')
        elif User.objects.filter(username=username).exists():
            messages.error(request, f'El usuario "{username}" ya existe.')
        elif len(password) < 8:
            messages.error(request, 'La contraseña debe tener al menos 8 caracteres.')
        else:
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=medico.nombres,
                last_name=medico.apellidos,
                email=medico.email,
            )
            # Configurar perfil
            profile = user.profile
            profile.empresa = empresa
            profile.telefono = medico.telefono
            profile.rol = Role.objects.get(nombre='DOCTOR')
            profile.save()
            # Vincular médico
            medico.user = user
            medico.save()

            ActivityLog.objects.create(
                empresa=empresa, usuario=request.user,
                accion='CREAR', modelo='Usuario',
                descripcion=f'Usuario creado desde médico: {medico.nombre_completo}'
            )
            messages.success(
                request,
                f'Usuario "{username}" creado y vinculado a Dr. {medico.nombre_completo}.'
            )
            return redirect('lista_usuarios')

    context = {
        'title': f'Crear usuario para {medico.nombre_completo}',
        'medico': medico,
        'active': 'usuarios',
    }
    return render(request, 'usuarios/crear_desde_medico.html', context)


# ===========================================================================
#  GESTIÓN DINÁMICA DE ROLES
# ===========================================================================

@login_required
@permiso_requerido('ver_usuarios')
def lista_roles(request):
    """Lista todos los roles del sistema."""
    roles = Role.objects.all()
    context = {
        'title': 'Roles',
        'roles': roles,
        'active': 'roles',
    }
    return render(request, 'usuarios/roles_lista.html', context)


@login_required
@permiso_requerido('ver_usuarios')
def crear_rol(request):
    """Crea un nuevo rol."""
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip().upper()
        descripcion = request.POST.get('descripcion', '').strip()
        if not nombre:
            messages.error(request, 'El nombre del rol es obligatorio.')
        elif len(nombre) > 20:
            messages.error(request, 'El nombre no puede exceder 20 caracteres.')
        elif Role.objects.filter(nombre=nombre).exists():
            messages.error(request, f'El rol "{nombre}" ya existe.')
        else:
            Role.objects.create(nombre=nombre, descripcion=descripcion)
            messages.success(request, f'Rol "{nombre}" creado exitosamente.')
            return redirect('lista_roles')
    context = {'title': 'Crear Rol', 'active': 'roles'}
    return render(request, 'usuarios/rol_form.html', context)


@login_required
@permiso_requerido('ver_usuarios')
def editar_rol(request, rol_id):
    """Edita un rol existente."""
    rol = get_object_or_404(Role, id=rol_id)
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip().upper()
        descripcion = request.POST.get('descripcion', '').strip()
        if not nombre:
            messages.error(request, 'El nombre del rol es obligatorio.')
        elif len(nombre) > 20:
            messages.error(request, 'El nombre no puede exceder 20 caracteres.')
        elif Role.objects.filter(nombre=nombre).exclude(id=rol.id).exists():
            messages.error(request, f'El rol "{nombre}" ya existe.')
        else:
            rol.nombre = nombre
            rol.descripcion = descripcion
            rol.save()
            messages.success(request, f'Rol "{nombre}" actualizado.')
            return redirect('lista_roles')
    context = {'title': f'Editar {rol.get_nombre_display()}', 'rol': rol, 'active': 'roles'}
    return render(request, 'usuarios/rol_form.html', context)


@login_required
@permiso_requerido('ver_usuarios')
def eliminar_rol(request, rol_id):
    """Elimina un rol (solo si no tiene usuarios asignados)."""
    rol = get_object_or_404(Role, id=rol_id)
    if rol.profile_set.exists():
        messages.error(request, f'No se puede eliminar "{rol.get_nombre_display()}" porque tiene usuarios asignados.')
    else:
        rol.delete()
        messages.success(request, f'Rol "{rol.get_nombre_display()}" eliminado.')
    return redirect('lista_roles')


# ===========================================================================
#  GESTIÓN DINÁMICA DE PERMISOS
# ===========================================================================

@login_required
@permiso_requerido('ver_usuarios')
def lista_permisos(request):
    """Lista todos los permisos del sistema."""
    from core.models import Permiso
    permisos = Permiso.objects.all().order_by('modulo', 'nombre')
    context = {
        'title': 'Permisos',
        'permisos': permisos,
        'active': 'permisos',
    }
    return render(request, 'usuarios/permisos_lista.html', context)


@login_required
@permiso_requerido('ver_usuarios')
def crear_permiso(request):
    """Crea un nuevo permiso en el sistema."""
    from core.models import Permiso
    if request.method == 'POST':
        codigo = request.POST.get('codigo', '').strip()
        nombre = request.POST.get('nombre', '').strip()
        modulo = request.POST.get('modulo', '')
        descripcion = request.POST.get('descripcion', '').strip()
        if not codigo or not nombre or not modulo:
            messages.error(request, 'Código, nombre y módulo son obligatorios.')
        elif Permiso.objects.filter(codigo=codigo).exists():
            messages.error(request, f'El permiso "{codigo}" ya existe.')
        else:
            Permiso.objects.create(codigo=codigo, nombre=nombre, modulo=modulo, descripcion=descripcion)
            messages.success(request, f'Permiso "{nombre}" creado.')
            return redirect('lista_permisos')
    context = {
        'title': 'Crear Permiso',
        'modulos': Permiso.MODULO_CHOICES,
        'active': 'permisos',
    }
    return render(request, 'usuarios/permiso_form.html', context)


@login_required
@permiso_requerido('ver_usuarios')
def editar_permiso(request, permiso_id):
    """Edita un permiso existente."""
    from core.models import Permiso
    permiso = get_object_or_404(Permiso, id=permiso_id)
    if request.method == 'POST':
        permiso.codigo = request.POST.get('codigo', permiso.codigo).strip()
        permiso.nombre = request.POST.get('nombre', permiso.nombre).strip()
        permiso.modulo = request.POST.get('modulo', permiso.modulo)
        permiso.descripcion = request.POST.get('descripcion', '').strip()
        permiso.save()
        messages.success(request, f'Permiso "{permiso.nombre}" actualizado.')
        return redirect('lista_permisos')
    context = {
        'title': f'Editar {permiso.nombre}',
        'permiso': permiso,
        'modulos': Permiso.MODULO_CHOICES,
        'active': 'permisos',
    }
    return render(request, 'usuarios/permiso_form.html', context)


@login_required
@permiso_requerido('ver_usuarios')
def eliminar_permiso(request, permiso_id):
    """Elimina un permiso."""
    from core.models import Permiso
    permiso = get_object_or_404(Permiso, id=permiso_id)
    permiso.delete()
    messages.success(request, f'Permiso "{permiso.nombre}" eliminado.')
    return redirect('lista_permisos')


# ===========================================================================
#  ASIGNAR PERMISOS A UN ROL
# ===========================================================================

@login_required
@permiso_requerido('asignar_permisos')
def permisos_rol(request, rol_id):
    """Asigna permisos a un rol para la empresa actual."""
    from core.models import Permiso, PermisoRol
    empresa = _get_empresa(request)
    if not empresa:
        messages.error(request, 'No se encontró la empresa.')
        return redirect('dashboard')

    rol = get_object_or_404(Role, id=rol_id)

    if request.method == 'POST':
        PermisoRol.objects.filter(empresa=empresa, rol=rol).delete()
        codigos = request.POST.getlist('permisos')
        for codigo in codigos:
            try:
                permiso = Permiso.objects.get(codigo=codigo)
                PermisoRol.objects.create(empresa=empresa, rol=rol, permiso=permiso)
            except Permiso.DoesNotExist:
                pass
        messages.success(request, f'Permisos actualizados para rol "{rol.get_nombre_display()}".')
        return redirect('lista_roles')

    permisos = Permiso.objects.all().order_by('modulo', 'nombre')
    asignados = PermisoRol.objects.filter(
        empresa=empresa, rol=rol
    ).values_list('permiso__codigo', flat=True)

    context = {
        'title': f'Permisos - {rol.get_nombre_display()}',
        'rol': rol,
        'permisos': permisos,
        'permisos_asignados': list(asignados),
        'active': 'roles',
    }
    return render(request, 'usuarios/permisos_rol.html', context)
