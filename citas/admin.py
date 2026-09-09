from django.contrib import admin
from .models import Cita


@admin.register(Cita)
class CitaAdmin(admin.ModelAdmin):
    list_display = ('paciente', 'fecha', 'hora', 'doctor', 'estado')
    list_filter = ('estado', 'fecha', 'doctor')
    search_fields = ('paciente__nombres', 'paciente__apellidos', 'motivo')
    date_hierarchy = 'fecha'
