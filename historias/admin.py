from django.contrib import admin
from .models import HistoriaClinica, Evolucion


@admin.register(HistoriaClinica)
class HistoriaClinicaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'tipo_sangre', 'fumador', 'fecha_creacion')
    search_fields = ('paciente__nombres', 'paciente__apellidos')


@admin.register(Evolucion)
class EvolucionAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'historia', 'medico', 'motivo')
    list_filter = ('fecha', 'medico')
