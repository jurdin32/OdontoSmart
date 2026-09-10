"""
Modo CLÍNICA ÚNICA (OdontSmart).

La aplicación está pensada para una sola clínica: no hay subdominios ni
selección de empresa. Todas las peticiones trabajan con la misma empresa
(el registro único de `core.Empresa`).
"""

from django.utils.deprecation import MiddlewareMixin


class EmpresaMiddleware(MiddlewareMixin):
    """Asigna la clínica única del sistema a cada request."""

    def process_request(self, request):
        from core.models import Empresa
        request.empresa = Empresa.get_solo()


def get_empresa(request=None):
    """Devuelve la clínica única del sistema.

    Funciona con o sin middleware: si el request ya trae la empresa la
    reutiliza; en caso contrario consulta el registro único de `Empresa`.
    """
    from core.models import Empresa
    if request is not None:
        empresa = getattr(request, 'empresa', None)
        if empresa is not None:
            return empresa
    return Empresa.get_solo()


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
