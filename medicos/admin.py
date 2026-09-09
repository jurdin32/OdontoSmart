from django.contrib import admin
from .models import Medico


@admin.register(Medico)
class MedicoAdmin(admin.ModelAdmin):
    list_display = ('apellidos', 'nombres', 'especialidad', 'registro_profesional', 'telefono', 'activo')
    list_filter = ('especialidad', 'activo')
    search_fields = ('nombres', 'apellidos', 'cedula', 'registro_profesional')
