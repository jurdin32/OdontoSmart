"""Modo clínica única.

OdontSmart pasa a funcionar con una sola clínica:
- Asigna la clínica existente a los registros que quedaron con `empresa = NULL`
  (datos creados antes de asociarlos, p. ej. perfiles o actividad).

No crea ninguna clínica: si no existe, se crea con `python manage.py seed_clinica`.
"""

from django.db import migrations


# (app_label, model_name) con FK `empresa`
MODELOS_CON_EMPRESA = [
    ('usuarios', 'Profile'),
    ('usuarios', 'ActivityLog'),
    ('citas', 'Cita'),
    ('facturacion', 'Proforma'),
    ('facturacion', 'Factura'),
    ('facturacion', 'Servicio'),
    ('historias', 'HistoriaClinica'),
    ('historias', 'Evolucion'),
    ('historias', 'Odontograma'),
    ('medicos', 'Medico'),
    ('pacientes', 'Paciente'),
    ('core', 'BackgroundTaskLog'),
]


def unificar_clinica(apps, schema_editor):
    Empresa = apps.get_model('core', 'Empresa')

    empresa = (
        Empresa.objects.filter(activo=True).order_by('id').first()
        or Empresa.objects.order_by('id').first()
    )
    if empresa is None:
        # Sin clínica configurada: no creamos datos automáticamente.
        return

    for app_label, model_name in MODELOS_CON_EMPRESA:
        try:
            Model = apps.get_model(app_label, model_name)
        except LookupError:
            continue
        # `.filter(empresa__isnull=True)` es seguro aunque el campo no sea nulo
        Model.objects.filter(empresa__isnull=True).update(empresa=empresa)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_alter_permiso_modulo'),
        ('usuarios', '0003_activitylog_empresa_profile_empresa_and_more'),
        ('citas', '0005_cita_servicio'),
        ('facturacion', '0002_servicio'),
        ('historias', '0012_evolucion_servicio'),
        ('medicos', '0003_medico_empresa_alter_medico_cedula_alter_medico_id_and_more'),
        ('pacientes', '0005_paciente_empresa_alter_paciente_cedula_and_more'),
    ]

    operations = [
        migrations.RunPython(unificar_clinica, migrations.RunPython.noop),
    ]
