from django.contrib import admin
from .models import BackgroundTaskLog


@admin.register(BackgroundTaskLog)
class BackgroundTaskLogAdmin(admin.ModelAdmin):
    list_display = ['tarea', 'estado', 'detalle_corto', 'ejecutado_por', 'fecha_ejecucion', 'duracion_segundos']
    list_filter = ['tarea', 'estado', 'fecha_ejecucion']
    search_fields = ['detalle', 'tarea']
    readonly_fields = ['fecha_ejecucion']

    def detalle_corto(self, obj):
        return obj.detalle[:80] if obj.detalle else '-'
    detalle_corto.short_description = 'Detalle'
