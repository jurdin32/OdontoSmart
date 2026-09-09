"""
Tareas en segundo plano (background jobs) para el consultorio odontológico.

Requiere:
    pip install django-background-tasks

Ejecutar el worker:
    python manage.py process_tasks

O usar Celery (más escalable):
    pip install celery redis
"""
import logging
from datetime import date, timedelta, datetime
from io import StringIO

from django.core.mail import send_mail
from django.db.models import Count
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings

logger = logging.getLogger(__name__)

# ============================================================================
#  TAREA 1: Recordatorios de citas (WhatsApp / Correo)
# ============================================================================

def enviar_recordatorios_citas():
    """
    Envía recordatorios de citas programadas para mañana.
    Ejecutar diario (ej: 8:00 AM).
    """
    from citas.models import Cita

    manana = date.today() + timedelta(days=1)
    citas = Cita.objects.filter(
        fecha=manana,
        estado__in=['PENDIENTE', 'CONFIRMADA']
    ).select_related('paciente', 'doctor')

    enviados = 0
    for cita in citas:
        paciente = cita.paciente
        doctor = cita.doctor

        # ---- Recordatorio por correo ----
        if paciente.email:
            try:
                asunto = '🔔 Recordatorio de cita - Dental D&D'
                mensaje = render_to_string('core/email_recordatorio_cita.txt', {
                    'paciente': paciente,
                    'cita': cita,
                    'doctor': doctor,
                })
                send_mail(
                    asunto, mensaje,
                    settings.DEFAULT_FROM_EMAIL or 'no-reply@dentaldd.com',
                    [paciente.email],
                    fail_silently=True,
                )
                logger.info(f'Correo enviado a {paciente.email} para cita {cita.id}')
                enviados += 1
            except Exception as e:
                logger.error(f'Error enviando correo a {paciente.email}: {e}')

        # ---- Recordatorio por WhatsApp (placeholder) ----
        # Integrar con Twilio / Meta API aquí
        if paciente.celular:
            try:
                _enviar_whatsapp_placeholder(paciente, cita)
                logger.info(f'WhatsApp enviado a {paciente.celular}')
                enviados += 1
            except Exception as e:
                logger.error(f'Error WhatsApp a {paciente.celular}: {e}')

    logger.info(f'Recordatorios enviados: {enviados}')
    return enviados


def _enviar_whatsapp_placeholder(paciente, cita):
    """
    Placeholder para integración con API de WhatsApp.
    Reemplazar con Twilio / WATI / Meta Cloud API.
    """
    from core.models import BackgroundTaskLog
    mensaje = (
        f'🦷 Recordatorio Dental D&D\n\n'
        f'Hola {paciente.nombres}, te recordamos tu cita:\n'
        f'📅 {cita.fecha.strftime("%d/%m/%Y")}\n'
        f'⏰ {cita.hora.strftime("%H:%M")}\n'
        f'👨‍⚕️ Dr. {cita.doctor}\n\n'
        f'📍 Confirma o reagenda: [enlace]'
    )
    # TODO: Integrar API real de WhatsApp
    BackgroundTaskLog.objects.create(
        tarea='ENVIAR_WHATSAPP',
        estado='SIMULADO',
        detalle=f'WhatsApp simulado para {paciente.celular}: {mensaje[:100]}...'
    )
    return True


# ============================================================================
#  TAREA 2: Generar facturación / reporte del mes
# ============================================================================

def generar_facturacion_mensual(mes=None, año=None):
    """
    Genera un resumen de facturación mensual con costos de evoluciones.
    """
    from historias.models import Evolucion

    now = timezone.localtime()
    mes = mes or now.month
    año = año or now.year

    evoluciones = Evolucion.objects.filter(
        fecha__year=año,
        fecha__month=mes,
        costo__isnull=False,
    ).select_related('historia__paciente', 'medico')

    total_general = 0
    resumen_medicos = {}

    for evol in evoluciones:
        total_general += float(evol.costo or 0)
        medico_nombre = str(evol.medico) if evol.medico else 'Sin médico'
        if medico_nombre not in resumen_medicos:
            resumen_medicos[medico_nombre] = {'cantidad': 0, 'total': 0.0}
        resumen_medicos[medico_nombre]['cantidad'] += 1
        resumen_medicos[medico_nombre]['total'] += float(evol.costo or 0)

    # Guardar en log
    from core.models import BackgroundTaskLog
    BackgroundTaskLog.objects.create(
        tarea='FACTURACION_MENSUAL',
        estado='COMPLETADO',
        detalle=(
            f'Facturación {mes}/{año}: '
            f'${total_general:,.2f} total, '
            f'{len(evoluciones)} tratamientos, '
            f'{len(resumen_medicos)} médicos'
        ),
    )

    logger.info(f'Facturación {mes}/{año}: ${total_general:,.2f}')
    return {'total': total_general, 'medicos': resumen_medicos, 'count': len(evoluciones)}


# ============================================================================
#  TAREA 3: Respaldar base de datos
# ============================================================================

def respaldar_base_datos():
    """
    Genera un respaldo de la base de datos SQLite usando el módulo
    sqlite3 de Python (no requiere sqlite3 CLI instalado).
    Para PostgreSQL usar pg_dump.
    """
    import sqlite3
    import gzip
    from pathlib import Path

    backup_dir = settings.BASE_DIR / 'backups'
    backup_dir.mkdir(exist_ok=True)

    timestamp = timezone.localtime().strftime('%Y%m%d_%H%M%S')
    backup_name = f'backup_{timestamp}.sql.gz'
    backup_gz_path = backup_dir / backup_name

    try:
        db_path = settings.BASE_DIR / 'db.sqlite3'
        if not db_path.exists():
            raise FileNotFoundError(f'Base de datos no encontrada: {db_path}')

        # Conectar y hacer dump vía Python sqlite3
        conn = sqlite3.connect(str(db_path))
        lines = []
        for line in conn.iterdump():
            lines.append(line)
        conn.close()

        sql_content = '\n'.join(lines)

        # Comprimir y guardar
        with gzip.open(str(backup_gz_path), 'wt', encoding='utf-8') as f:
            f.write(sql_content)

        # Limpiar backups antiguos (mayores a 30 días)
        limpiar_backups_antiguos(backup_dir, dias=30)

        from core.models import BackgroundTaskLog
        BackgroundTaskLog.objects.create(
            tarea='RESPALDO_DB',
            estado='COMPLETADO',
            detalle=f'Backup creado: {backup_name} ({len(sql_content)} bytes)',
        )
        logger.info(f'Backup creado: {backup_gz_path}')
        return str(backup_gz_path)

    except Exception as e:
        from core.models import BackgroundTaskLog
        BackgroundTaskLog.objects.create(
            tarea='RESPALDO_DB',
            estado='ERROR',
            detalle=str(e),
        )
        logger.error(f'Error respaldando BD: {e}')
        raise


def limpiar_backups_antiguos(backup_dir, dias=30):
    """Elimina backups con más de `dias` de antigüedad."""
    from pathlib import Path
    ahora = timezone.localtime()
    for f in Path(backup_dir).glob('backup_*.sql*'):
        try:
            if f.stat().st_mtime < (ahora - timedelta(days=dias)).timestamp():
                f.unlink()
                logger.info(f'Backup antiguo eliminado: {f.name}')
        except (FileNotFoundError, OSError):
            pass


# ============================================================================
#  TAREA 4: Limpiar locks expirados (mantenimiento)
# ============================================================================

def limpiar_locks_expirados():
    """
    Limpia locks de edición expirados del sistema de concurrencia.
    Ejecutar periódicamente (ej: cada hora).
    """
    from django.core.cache import cache
    # Los locks expiran automáticamente vía timeout de cache.
    # Esta tarea es solo para logging.
    from core.models import BackgroundTaskLog
    BackgroundTaskLog.objects.create(
        tarea='LIMPIEZA_LOCKS',
        estado='COMPLETADO',
        detalle='Locks expirados limpiados automáticamente por timeout.',
    )
    logger.info('Limpieza de locks completada.')
