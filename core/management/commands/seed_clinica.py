"""Crea la clínica única del sistema si no existe.

OdontSmart funciona en modo de una sola clínica. En una instalación nueva
no hay ninguna `Empresa`, así que este comando crea la clínica por defecto.

Uso:
    python manage.py seed_clinica
    python manage.py seed_clinica --nombre "Dental D & D" --ruc 0000000000001
"""

from django.core.management.base import BaseCommand

from core.models import Empresa


class Command(BaseCommand):
    help = 'Crea la clínica única de OdontSmart si todavía no existe'

    def add_arguments(self, parser):
        parser.add_argument('--nombre', default='Mi Clínica')
        parser.add_argument('--ruc', default='9999999999999')

    def handle(self, *args, **options):
        if Empresa.objects.exists():
            empresa = Empresa.get_solo()
            self.stdout.write(self.style.WARNING(
                f'Ya existe una clínica: {empresa.nombre} (id={empresa.id}). '
                'No se creó ninguna nueva.'
            ))
            return

        empresa = Empresa.objects.create(
            nombre=options['nombre'],
            ruc=options['ruc'],
            activo=True,
        )
        self.stdout.write(self.style.SUCCESS(
            f'Clínica creada: {empresa.nombre} (id={empresa.id})'
        ))
