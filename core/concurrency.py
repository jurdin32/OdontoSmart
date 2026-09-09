"""
Sistema de Control de Concurrencia para el consultorio odontológico.

Proporciona:
- Bloqueo optimista (version field) para detectar conflictos de edición.
- Bloqueo pesimista (cache en DB) para impedir ediciones simultáneas.
- Utilidades para vistas y templates.
"""
import json
import logging
from datetime import datetime, timedelta

from django.db import models, transaction
from django.core.cache import cache
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
#  Model Mixin – Bloqueo optimista (version field)
# ---------------------------------------------------------------------------

class VersionLockMixin(models.Model):
    """
    Añade un campo `version` que se incrementa en cada save().
    Úsalo como clase base (mixín) en los modelos editables.

    Al guardar, si el objeto fue modificado por otro proceso, levanta
    una excepción ConcurrentUpdateError.
    """
    version = models.PositiveIntegerField(
        default=1,
        verbose_name='Versión',
        help_text='Número de versión para control de concurrencia'
    )

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        """Incrementa la versión en cada save."""
        # Si estamos forzando un update (sin concurrencia), saltamos check
        skip_version_check = kwargs.pop('skip_version_check', False)

        if not skip_version_check and self.pk:
            # Bloqueo optimista: la versión en BD debe coincidir
            with transaction.atomic():
                # Bloqueamos la fila para evitar race conditions
                locked = type(self).objects.select_for_update().filter(
                    pk=self.pk, version=self.version
                )
                if locked.exists():
                    self.version = models.F('version') + 1
                    super().save(*args, **kwargs)
                    # Refrescamos el objeto para tener la versión real
                    if self.pk:
                        self.refresh_from_db()
                else:
                    current = type(self).objects.filter(pk=self.pk).first()
                    if current and current.version != self.version:
                        raise ConcurrentUpdateError(
                            self._meta.verbose_name or type(self).__name__,
                            self.pk,
                            current.version,
                            self.version
                        )
                    super().save(*args, **kwargs)
        else:
            super().save(*args, **kwargs)

    def save_without_version_check(self, *args, **kwargs):
        """Guarda sin verificar la versión (para migraciones / tareas internas)."""
        return self.save(*args, **kwargs, skip_version_check=True)


class ConcurrentUpdateError(Exception):
    """Se lanza cuando un registro fue modificado por otro usuario."""

    def __init__(self, model_name, object_id, current_version, expected_version):
        self.model_name = model_name
        self.object_id = object_id
        self.current_version = current_version
        self.expected_version = expected_version
        super().__init__(
            f'"{model_name}" (ID {object_id}) fue modificado por otro usuario. '
            f'Tu versión: v{expected_version}, versión actual: v{current_version}. '
            'Por favor recarga la página y vuelve a intentarlo.'
        )


# ---------------------------------------------------------------------------
#  Pesimistic Locking – Bloqueo a nivel de edición (cache en BD)
# ---------------------------------------------------------------------------

LOCK_TIMEOUT = 30  # minutos antes de expirar el lock
LOCK_PREFIX = 'edit_lock'


def acquire_lock(model_name: str, object_id: int, user: User) -> bool:
    """
    Intenta adquirir un lock de edición para un registro.
    Retorna True si se adquirió el lock, False si otro usuario lo tiene.
    """
    lock_key = f'{LOCK_PREFIX}:{model_name}:{object_id}'
    lock_data = cache.get(lock_key)

    if lock_data:
        # Ya hay un lock – verificamos si es del mismo usuario
        owner_id = lock_data.get('user_id')
        if owner_id == user.id:
            # Mismo usuario – renovamos el lock
            extend_lock(model_name, object_id, user)
            return True
        # Verificar si el lock expiró
        acquired_at = datetime.fromisoformat(lock_data.get('acquired_at', ''))
        if timezone.now() - acquired_at > timedelta(minutes=LOCK_TIMEOUT):
            # Lock expirado – lo reasignamos
            _set_lock(lock_key, model_name, object_id, user)
            return True
        return False  # Otro usuario tiene el lock activo

    # No hay lock – lo creamos
    _set_lock(lock_key, model_name, object_id, user)
    return True


def _set_lock(lock_key: str, model_name: str, object_id: int, user: User):
    """Establece un lock en caché con timeout."""
    lock_data = {
        'user_id': user.id,
        'username': user.get_full_name() or user.username,
        'model_name': model_name,
        'object_id': object_id,
        'acquired_at': timezone.now().isoformat(),
    }
    cache.set(lock_key, lock_data, timeout=LOCK_TIMEOUT * 60)


def extend_lock(model_name: str, object_id: int, user: User) -> bool:
    """Extiende el tiempo de un lock existente."""
    lock_key = f'{LOCK_PREFIX}:{model_name}:{object_id}'
    lock_data = cache.get(lock_key)
    if lock_data and lock_data.get('user_id') == user.id:
        lock_data['acquired_at'] = timezone.now().isoformat()
        cache.set(lock_key, lock_data, timeout=LOCK_TIMEOUT * 60)
        return True
    return False


def release_lock(model_name: str, object_id: int, user: User):
    """Libera el lock de edición."""
    lock_key = f'{LOCK_PREFIX}:{model_name}:{object_id}'
    lock_data = cache.get(lock_key)
    if lock_data and lock_data.get('user_id') == user.id:
        cache.delete(lock_key)


def get_lock_info(model_name: str, object_id: int) -> dict | None:
    """Retorna información del lock activo, o None si no hay lock."""
    lock_key = f'{LOCK_PREFIX}:{model_name}:{object_id}'
    return cache.get(lock_key)


def is_locked_by_other(model_name: str, object_id: int, user: User) -> bool:
    """Verifica si el registro está bloqueado por OTRO usuario."""
    lock_info = get_lock_info(model_name, object_id)
    if lock_info:
        return lock_info.get('user_id') != user.id
    return False


def get_locker_user(model_name: str, object_id: int) -> str | None:
    """Retorna el nombre del usuario que tiene el lock, o None."""
    lock_info = get_lock_info(model_name, object_id)
    if lock_info:
        return lock_info.get('username')
    return None


# ---------------------------------------------------------------------------
#  Utilidad: decorador para views que necesitan control de concurrencia
# ---------------------------------------------------------------------------

from functools import wraps


def with_concurrency_control(model_getter, model_name=None):
    """
    Decorador para vistas de edición que gestiona locks.

    Uso:
        @with_concurrency_control(lambda r, pid: (Paciente, pid, 'Paciente'))
        def editar_paciente(request, paciente_id): ...

    El decorador:
    1. Adquiere un lock al entrar (GET).
    2. Libera el lock al guardar exitosamente (POST exitoso).
    3. Muestra error si otro usuario tiene el lock.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            model, obj_id, m_name = model_getter(request, *args, **kwargs)
            name = model_name or m_name

            # Verificar si hay lock de otro usuario
            if is_locked_by_other(name, obj_id, request.user):
                locker = get_locker_user(name, obj_id)
                from django.contrib import messages
                messages.warning(
                    request,
                    f'⚠️ Este registro está siendo editado por {locker}. '
                    'Los cambios podrían sobrescribirse. Edita con precaución.'
                )

            # Adquirir / renovar lock
            if request.method == 'GET':
                acquire_lock(name, obj_id, request.user)

            response = view_func(request, *args, **kwargs)

            # Liberar lock si se guardó exitosamente (redirect = éxito)
            if request.method == 'POST' and hasattr(response, 'status_code') and response.status_code == 302:
                release_lock(name, obj_id, request.user)
            elif request.method == 'POST' and hasattr(response, 'status_code') and response.status_code == 200:
                # Hubo error en el form – extendemos lock
                extend_lock(name, obj_id, request.user)

            return response
        return _wrapped_view
    return decorator
