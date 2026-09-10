"""
Management command para sembrar permisos del sistema OdontSmart.
Ejecutar después de migrar: python manage.py seed_permisos
"""

from django.core.management.base import BaseCommand
from core.models import Permiso


PERMISOS = [
    # ====== PACIENTES ======
    ('Ver lista de pacientes', 'ver_pacientes', 'PACIENTES'),
    ('Ver detalle de paciente', 'ver_detalle_paciente', 'PACIENTES'),
    ('Crear pacientes', 'crear_pacientes', 'PACIENTES'),
    ('Editar pacientes', 'editar_pacientes', 'PACIENTES'),
    ('Eliminar pacientes', 'eliminar_pacientes', 'PACIENTES'),
    ('Ver foto del paciente', 'ver_foto_paciente', 'PACIENTES'),

    # ====== MÉDICOS ======
    ('Ver lista de médicos', 'ver_medicos', 'MEDICOS'),
    ('Ver detalle de médico', 'ver_detalle_medico', 'MEDICOS'),
    ('Crear médicos', 'crear_medicos', 'MEDICOS'),
    ('Editar médicos', 'editar_medicos', 'MEDICOS'),
    ('Eliminar médicos', 'eliminar_medicos', 'MEDICOS'),

    # ====== CITAS ======
    ('Ver lista de citas', 'ver_citas', 'CITAS'),
    ('Ver detalle de cita', 'ver_detalle_cita', 'CITAS'),
    ('Crear citas', 'crear_citas', 'CITAS'),
    ('Editar citas', 'editar_citas', 'CITAS'),
    ('Eliminar citas', 'eliminar_citas', 'CITAS'),
    ('Cambiar estado de cita', 'cambiar_estado_cita', 'CITAS'),

    # ====== HISTORIAS CLÍNICAS ======
    ('Ver historia clínica', 'ver_historia', 'HISTORIAS'),
    ('Editar historia clínica', 'editar_historia', 'HISTORIAS'),
    ('Ver odontograma', 'ver_odontograma', 'HISTORIAS'),
    ('Editar odontograma', 'editar_odontograma', 'HISTORIAS'),
    ('Crear evolución', 'crear_evolucion', 'HISTORIAS'),
    ('Editar evolución', 'editar_evolucion', 'HISTORIAS'),
    ('Eliminar evolución', 'eliminar_evolucion', 'HISTORIAS'),
    ('Imprimir consentimiento', 'imprimir_consentimiento', 'HISTORIAS'),

    # ====== REPORTES ======
    ('Ver dashboard de reportes', 'ver_reportes', 'REPORTES'),
    ('Ver reporte de pacientes', 'ver_reporte_pacientes', 'REPORTES'),
    ('Ver reporte de citas', 'ver_reporte_citas', 'REPORTES'),
    ('Ver reporte de médicos', 'ver_reporte_medicos', 'REPORTES'),
    ('Ver reporte de historias', 'ver_reporte_historias', 'REPORTES'),
    ('Ver reporte de actividad', 'ver_reporte_actividad', 'REPORTES'),
    ('Ver reporte de valores', 'ver_reporte_valores', 'REPORTES'),

    # ====== USUARIOS ======
    ('Ver lista de usuarios', 'ver_usuarios', 'USUARIOS'),
    ('Crear usuarios', 'crear_usuarios', 'USUARIOS'),
    ('Editar usuarios', 'editar_usuarios', 'USUARIOS'),
    ('Asignar permisos', 'asignar_permisos', 'USUARIOS'),

    # ====== CONFIGURACIÓN ======
    ('Ver configuración', 'ver_configuracion', 'CONFIGURACION'),
    ('Editar configuración', 'editar_configuracion', 'CONFIGURACION'),
    ('Editar perfil de empresa', 'editar_perfil_empresa', 'CONFIGURACION'),

    # ====== TAREAS ======
    ('Ver tareas programadas', 'ver_tareas', 'TAREAS'),
    ('Ejecutar tareas', 'ejecutar_tareas', 'TAREAS'),
    ('Eliminar logs de tareas', 'eliminar_logs_tareas', 'TAREAS'),

    # ====== FACTURACIÓN ======
    ('Ver lista de facturas', 'ver_facturas', 'FACTURACION'),
    ('Crear facturas', 'crear_facturas', 'FACTURACION'),
    ('Editar facturas', 'editar_facturas', 'FACTURACION'),
    ('Eliminar facturas', 'eliminar_facturas', 'FACTURACION'),
    ('Ver proformas', 'ver_proformas', 'FACTURACION'),
    ('Crear proformas', 'crear_proformas', 'FACTURACION'),
    ('Editar proformas', 'editar_proformas', 'FACTURACION'),
    ('Eliminar proformas', 'eliminar_proformas', 'FACTURACION'),

    # ====== SRI ======
    ('Configuración SRI', 'sri_config', 'SRI'),
    ('Emitir comprobantes electrónicos', 'sri_emitir', 'SRI'),
    ('Consultar autorizaciones SRI', 'sri_consultar', 'SRI'),

    # ====== SERVICIOS ======
    ('Ver servicios', 'ver_servicios', 'SERVICIOS'),
    ('Crear servicios', 'crear_servicios', 'SERVICIOS'),
    ('Editar servicios', 'editar_servicios', 'SERVICIOS'),
    ('Eliminar servicios', 'eliminar_servicios', 'SERVICIOS'),
]


class Command(BaseCommand):
    help = 'Crea los permisos del sistema OdontSmart'

    def handle(self, *args, **options):
        creados = 0
        for nombre, codigo, modulo in PERMISOS:
            _, created = Permiso.objects.get_or_create(
                codigo=codigo,
                defaults={'nombre': nombre, 'modulo': modulo}
            )
            if created:
                creados += 1
                self.stdout.write(f'  ✓ {codigo}')
        self.stdout.write(self.style.SUCCESS(
            f'\n{creados} permisos creados exitosamente'
        ))
