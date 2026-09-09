"""
Management command para ejecutar tareas programadas manualmente.

Uso:
    python manage.py run_tareas recordatorios
    python manage.py run_tareas facturacion --mes 6 --año 2025
    python manage.py run_tareas respaldo
    python manage.py run_tareas todas
"""
import time
import logging
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from core.tasks import (
    enviar_recordatorios_citas,
    generar_facturacion_mensual,
    respaldar_base_datos,
    limpiar_locks_expirados,
)
from core.models import BackgroundTaskLog

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Ejecuta tareas programadas del sistema'

    def add_arguments(self, parser):
        parser.add_argument(
            'tarea',
            type=str,
            choices=['recordatorios', 'facturacion', 'respaldo', 'limpieza', 'todas'],
            help='Nombre de la tarea a ejecutar'
        )
        parser.add_argument(
            '--mes', type=int, default=None,
            help='Mes para facturación (1-12)'
        )
        parser.add_argument(
            '--año', type=int, default=None,
            help='Año para facturación'
        )

    def handle(self, *args, **options):
        tarea = options['tarea']
        mes = options.get('mes')
        año = options.get('año')

        tareas_map = {
            'recordatorios': ('RECORDATORIO_CITAS', enviar_recordatorios_citas),
            'facturacion': ('FACTURACION_MENSUAL',
                          lambda: generar_facturacion_mensual(mes or date.today().month,
                                                              año or date.today().year)),
            'respaldo': ('RESPALDO_DB', respaldar_base_datos),
            'limpieza': ('LIMPIEZA_LOCKS', limpiar_locks_expirados),
        }

        if tarea == 'todas':
            for nombre, (codigo, fn) in tareas_map.items():
                self._ejecutar(codigo, fn)
        else:
            codigo, fn = tareas_map[tarea]
            self._ejecutar(codigo, fn)

    def _ejecutar(self, codigo, fn):
        log = BackgroundTaskLog.objects.create(
            tarea=codigo,
            estado='EN_PROCESO',
            detalle='Iniciando...',
        )
        inicio = time.time()
        try:
            resultado = fn()
            duracion = time.time() - inicio
            log.estado = 'COMPLETADO'
            log.detalle = str(resultado) if resultado else 'Completado'
            log.duracion_segundos = duracion
            log.save()
            self.stdout.write(
                self.style.SUCCESS(f'✅ {codigo} completado en {duracion:.1f}s')
            )
        except Exception as e:
            duracion = time.time() - inicio
            log.estado = 'ERROR'
            log.detalle = str(e)
            log.duracion_segundos = duracion
            log.save()
            self.stdout.write(
                self.style.ERROR(f'❌ {codigo} falló: {e}')
            )
