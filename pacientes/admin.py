from django.contrib import admin
from .models import Paciente


@admin.register(Paciente)
class PacienteAdmin(admin.ModelAdmin):
    list_display = ('apellidos', 'nombres', 'cedula', 'edad', 'telefono', 'activo')
    list_filter = ('genero', 'activo', 'fecha_registro')
    search_fields = ('nombres', 'apellidos', 'cedula', 'telefono')
    ordering = ('apellidos',)
