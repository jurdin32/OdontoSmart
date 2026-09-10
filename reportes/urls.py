from django.urls import path
from . import views

urlpatterns = [
    path('', views.reportes_dashboard, name='reportes'),
    path('pacientes/', views.reporte_pacientes, name='reporte_pacientes'),
    path('citas/', views.reporte_citas, name='reporte_citas'),
    path('medicos/', views.reporte_medicos, name='reporte_medicos'),
    path('historias/', views.reporte_historias, name='reporte_historias'),
    path('actividad/', views.reporte_actividad, name='reporte_actividad'),
    path('valores/', views.reporte_valores, name='reporte_valores'),
    path('facturas/', views.reporte_facturas, name='reporte_facturas'),
    path('servicios/', views.reporte_servicios, name='reporte_servicios'),
    path('facturas/excel/', views.exportar_facturas_excel, name='exportar_facturas_excel'),
    path('facturas/pdf/', views.exportar_facturas_pdf, name='exportar_facturas_pdf'),
]
