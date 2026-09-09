from django.urls import path
from . import views

urlpatterns = [
    # Proformas
    path('proformas/', views.lista_proformas, name='lista_proformas'),
    path('proformas/registrar/', views.crear_proforma, name='crear_proforma'),
    path('proformas/<int:proforma_id>/', views.detalle_proforma, name='detalle_proforma'),
    path('proformas/<int:proforma_id>/editar/', views.editar_proforma, name='editar_proforma'),
    path('proformas/<int:proforma_id>/eliminar/', views.eliminar_proforma, name='eliminar_proforma'),
    path('proformas/<int:proforma_id>/facturar/', views.proforma_a_factura, name='proforma_a_factura'),
    # Facturas
    path('facturas/', views.lista_facturas, name='lista_facturas'),
    path('facturas/registrar/', views.crear_factura, name='crear_factura'),
    path('facturas/<int:factura_id>/', views.detalle_factura, name='detalle_factura'),
    path('facturas/<int:factura_id>/editar/', views.editar_factura, name='editar_factura'),
    path('facturas/<int:factura_id>/eliminar/', views.eliminar_factura, name='eliminar_factura'),
    path('facturas/<int:factura_id>/pagar/', views.registrar_pago, name='registrar_pago'),
    # Print
    path('proformas/<int:proforma_id>/imprimir/', views.imprimir_proforma, name='imprimir_proforma'),
    path('facturas/<int:factura_id>/imprimir/', views.imprimir_factura, name='imprimir_factura'),
]
