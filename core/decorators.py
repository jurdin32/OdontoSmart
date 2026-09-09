"""
Decoradores para el sistema de permisos dinámico de OdontSmart.
"""

from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse


def permiso_requerido(codigo_permiso):
    """
    Decorador que verifica si el usuario tiene un permiso específico.
    Uso: @permiso_requerido('ver_pacientes')

    Si no tiene el permiso, redirige al dashboard con mensaje de error.
    Los superusuarios pasan automáticamente.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')

            # Superusuarios pasan siempre
            if request.user.is_superuser:
                return view_func(request, *args, **kwargs)

            # Verificar permiso
            from core.tenant import get_empresa, tiene_permiso
            empresa = get_empresa(request)

            if tiene_permiso(request.user, codigo_permiso, empresa):
                return view_func(request, *args, **kwargs)

            # Sin permiso
            messages.error(
                request,
                'No tienes permiso para realizar esta acción.'
            )
            return redirect('dashboard')
        return _wrapped_view
    return decorator


def empresa_requerida(view_func):
    """
    Decorador que verifica que exista una empresa en el request.
    Si no hay empresa, redirige al login.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        from core.tenant import get_empresa
        empresa = get_empresa(request)

        if not empresa:
            messages.error(
                request,
                'No se pudo identificar la empresa. Acceso denegado.'
            )
            return redirect('login')
        return view_func(request, *args, **kwargs)
    return _wrapped_view
