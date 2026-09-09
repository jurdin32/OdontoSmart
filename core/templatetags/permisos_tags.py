from django import template
from django.conf import settings

register = template.Library()


def _check_permiso(request, codigo_permiso):
    """Función interna para verificar permiso."""
    if not request or not request.user.is_authenticated:
        return False

    if request.user.is_superuser:
        return True

    from core.tenant import tiene_permiso
    empresa = getattr(request, 'empresa', None)
    if not empresa:
        empresa = getattr(request.user.profile, 'empresa', None) if hasattr(request.user, 'profile') else None

    return tiene_permiso(request.user, codigo_permiso, empresa)


@register.simple_tag(takes_context=True)
def tiene_permiso(context, codigo_permiso):
    """
    Template tag para verificar si el usuario tiene un permiso específico.
    Uso: {% load permisos_tags %} {% tiene_permiso 'ver_pacientes' as puede_ver %}
    """
    request = context.get('request')
    return _check_permiso(request, codigo_permiso)





@register.simple_tag(takes_context=True)
def es_admin(context):
    """
    Template tag que verifica si el usuario es administrador.
    """
    request = context.get('request')
    if not request or not request.user.is_authenticated:
        return False

    if request.user.is_superuser:
        return True

    return (
        hasattr(request.user, 'profile') and
        request.user.profile.rol and
        request.user.profile.rol.nombre == 'ADMIN'
    )
