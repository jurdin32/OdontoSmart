from django.contrib import admin
from .models import Proforma, Factura


@admin.register(Proforma)
class ProformaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'paciente', 'total', 'estado', 'fecha_emision']
    list_filter = ['estado', 'empresa']
    search_fields = ['numero', 'paciente__nombres', 'paciente__apellidos']


@admin.register(Factura)
class FacturaAdmin(admin.ModelAdmin):
    list_display = ['numero', 'paciente', 'total', 'estado', 'forma_pago', 'fecha_emision']
    list_filter = ['estado', 'forma_pago', 'empresa']
    search_fields = ['numero', 'paciente__nombres', 'paciente__apellidos']
