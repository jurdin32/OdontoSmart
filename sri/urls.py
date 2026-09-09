from django.urls import path
from . import views

urlpatterns = [
    path('configuracion/', views.sri_configuracion, name='sri_configuracion'),
    path('documentos/', views.sri_documentos, name='sri_documentos'),
    path('log/', views.sri_log_view, name='sri_log'),
    path('emitir/<int:factura_id>/', views.emitir_factura_electronica, name='emitir_factura_electronica'),
    path('reintentar/<int:documento_id>/', views.reintentar_envio, name='reintentar_envio'),
    path('consultar/<int:documento_id>/', views.consultar_autorizacion, name='consultar_autorizacion'),
    path('verificar-certificado/', views.verificar_certificado, name='verificar_certificado'),
]
