from django.contrib import admin
from .models import SriEmpresaConfig, SriDocumento


@admin.register(SriEmpresaConfig)
class SriEmpresaConfigAdmin(admin.ModelAdmin):
    list_display = ['razon_social', 'ruc', 'ambiente', 'activo']
    list_filter = ['ambiente', 'activo']
    search_fields = ['razon_social', 'ruc']


@admin.register(SriDocumento)
class SriDocumentoAdmin(admin.ModelAdmin):
    list_display = [
        'numero_documento', 'tipo', 'estado',
        'created_at', 'total', 'ambiente',
    ]
    list_filter = ['tipo', 'estado', 'ambiente']
    search_fields = ['clave_acceso', 'numero_documento', 'identificacion_comprador']
    readonly_fields = ['clave_acceso', 'xml_firmado', 'xml_autorizado']
