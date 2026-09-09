"""
Middleware y utilidades para el sistema multi-tenant (OdontSmart).

Detecta la empresa desde:
1. Subdominio (producción): empresa1.odontsmart.com
2. Parámetro GET / sesión (desarrollo): ?empresa_id=1
3. Perfil del usuario autenticado (fallback)
"""

import re
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.urls import reverse


class EmpresaMiddleware(MiddlewareMixin):
    """
    Middleware que identifica la empresa actual desde el subdominio
    y la asigna a request.empresa.
    """

    def process_request(self, request):
        user = getattr(request, 'user', None)
        authed = bool(user and user.is_authenticated)

        # 1. Empresa por subdominio (identifica el tenant en producción)
        empresa_sub = self._get_empresa_from_subdomain(request)

        if authed:
            # Usuarios autenticados: la empresa SIEMPRE sale de su perfil.
            # No se respeta '?empresa_id=' ni un subdominio ajeno, para evitar
            # la suplantación de tenant (fuga de datos entre empresas).
            profile = getattr(user, 'profile', None)
            empresa = profile.empresa if (profile and profile.empresa_id) else None
        else:
            # Anónimos (login/landing): subdominio o '?empresa_id' (dev).
            empresa = empresa_sub
            if not empresa and 'empresa_id' in request.GET:
                from core.models import Empresa
                try:
                    empresa = Empresa.objects.get(
                        id=int(request.GET.get('empresa_id')),
                        activo=True
                    )
                except (Empresa.DoesNotExist, ValueError, TypeError):
                    pass

        # 2. Guardar en request y sesión
        request.empresa = empresa
        if empresa:
            request.session['empresa_id'] = empresa.id
        elif 'empresa_id' in request.session:
            # Si se cambió de sesión, limpiar
            del request.session['empresa_id']

    def _get_empresa_from_subdomain(self, request):
        """Extrae el subdominio del host y busca la empresa."""
        host = request.get_host().split(':')[0]  # quitar puerto
        # En desarrollo sin subdominio, retornar None
        if host in ('localhost', '127.0.0.1'):
            return None

        parts = host.split('.')
        if len(parts) < 3:
            return None

        subdomain = parts[0]
        if subdomain == 'www':
            return None

        from core.models import Empresa
        try:
            return Empresa.objects.get(subdominio=subdomain, activo=True)
        except Empresa.DoesNotExist:
            return None


def get_empresa(request):
    """
    Devuelve la empresa vigente para el request.

    Para usuarios autenticados el middleware ya garantiza que request.empresa
    coincide con la empresa de su perfil; aquí solo hay un fallback para
    contextos donde el middleware no corrió (tests, tareas, etc.).
    """
    empresa = getattr(request, 'empresa', None)
    if empresa:
        return empresa
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        profile = getattr(user, 'profile', None)
        if profile and profile.empresa_id:
            return profile.empresa
    return None


def empresa_context(request):
    """Context processor: agrega la empresa actual y su configuración al template."""
    empresa = getattr(request, 'empresa', None)
    config = None
    if empresa:
        try:
            config = empresa.configuracion
        except Exception:
            config = None

    return {
        'empresa': empresa,
        'config_empresa': config,
    }


def tiene_permiso(usuario, codigo_permiso, empresa=None):
    """
    Verifica si un usuario tiene un permiso específico en una empresa.
    Los superusuarios (admin Django) siempre tienen todos los permisos.
    También verifica los permisos asignados al rol del usuario (PermisoRol).
    """
    if usuario.is_superuser:
        return True
    if not empresa and hasattr(usuario, 'profile') and usuario.profile.empresa_id:
        empresa = usuario.profile.empresa

    if not empresa or not usuario.is_authenticated:
        return False

    from core.models import PermisoUsuario, PermisoRol, Permiso

    # 1. Verificar si el usuario tiene el permiso asignado individualmente
    if PermisoUsuario.objects.filter(
        empresa=empresa,
        usuario=usuario,
        permiso__codigo=codigo_permiso,
        concedido=True
    ).exists():
        return True

    # 2. Verificar si el rol del usuario tiene el permiso asignado
    rol = getattr(usuario.profile, 'rol', None) if hasattr(usuario, 'profile') else None
    if rol and PermisoRol.objects.filter(
        empresa=empresa,
        rol=rol,
        permiso__codigo=codigo_permiso
    ).exists():
        return True

    return False
