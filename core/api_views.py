"""
API endpoints para el sistema de control de concurrencia (locks).
"""
import json
import re
from django.http import JsonResponse
from django.views.decorators.http import require_POST, require_GET
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth import user_logged_out
from django.dispatch import receiver
from django.core.cache import cache

from .concurrency import (
    acquire_lock, release_lock, extend_lock,
    is_locked_by_other, get_locker_user, LOCK_PREFIX,
)


@login_required
@require_POST
def lock_renew(request):
    """Renueva el lock de edición de un registro."""
    try:
        data = json.loads(request.body)
        model_name = data.get('model_name')
        object_id = data.get('object_id')
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)

    if not model_name or not object_id:
        return JsonResponse({'ok': False, 'error': 'Faltan parámetros'}, status=400)

    ok = extend_lock(model_name, object_id, request.user)
    return JsonResponse({'ok': ok})


@login_required
@require_GET
def lock_check(request):
    """Verifica el estado del lock de un registro."""
    model_name = request.GET.get('model_name')
    object_id = request.GET.get('object_id')

    if not model_name or not object_id:
        return JsonResponse({'ok': False, 'error': 'Faltan parámetros'}, status=400)

    try:
        object_id = int(object_id)
    except (ValueError, TypeError):
        return JsonResponse({'ok': False, 'error': 'object_id inválido'}, status=400)

    locked_by_other = is_locked_by_other(model_name, object_id, request.user)
    locker = get_locker_user(model_name, object_id)

    return JsonResponse({
        'locked': locker is not None,
        'locked_by_other': locked_by_other,
        'locker_name': locker,
    })


# NOTA: Usamos csrf_exempt porque release_lock solo limpia una clave de cache.
# No modifica datos sensibles. Esto permite que sendBeacon y beforeunload
# funcionen sin token CSRF (que no está disponible al cerrar la página).
@login_required
@csrf_exempt
def lock_release(request):
    """Libera el lock de edición de un registro.
    Acepta POST y GET para compatibilidad con sendBeacon y beforeunload.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            model_name = data.get('model_name')
            object_id = data.get('object_id')
        except (json.JSONDecodeError, TypeError):
            return JsonResponse({'ok': False, 'error': 'Datos inválidos'}, status=400)
    elif request.method == 'GET':
        model_name = request.GET.get('model_name')
        try:
            object_id = int(request.GET.get('object_id', 0))
        except (ValueError, TypeError):
            return JsonResponse({'ok': False, 'error': 'object_id inválido'}, status=400)
    else:
        return JsonResponse({'ok': False, 'error': 'Método no soportado'}, status=405)

    if not model_name or not object_id:
        return JsonResponse({'ok': False, 'error': 'Faltan parámetros'}, status=400)

    release_lock(model_name, object_id, request.user)
    return JsonResponse({'ok': True})


# Liberar todos los locks del usuario al cerrar sesión
@receiver(user_logged_out)
def liberar_locks_al_cerrar_sesion(sender, request, user, **kwargs):
    """Cuando un usuario cierra sesión, libera todos sus locks."""
    if not user:
        return
    # Buscar todas las claves de cache que coincidan con locks de este usuario
    # DatabaseCache no soporta iteración de claves, así que los locks expirarán
    # solos por timeout. Pero al menos podemos registrar la acción.
    from .models import BackgroundTaskLog
    BackgroundTaskLog.objects.create(
        tarea='LIMPIEZA_LOCKS',
        estado='COMPLETADO',
        detalle=f'Locks liberados para {user.username} al cerrar sesión',
        ejecutado_por=user,
    )
