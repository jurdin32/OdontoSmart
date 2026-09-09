from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_citas, name='lista_citas'),
    path('registrar/', views.registrar_cita, name='registrar_cita'),
    path('<int:cita_id>/', views.detalle_cita, name='detalle_cita'),
    path('<int:cita_id>/editar/', views.editar_cita, name='editar_cita'),
    path('<int:cita_id>/eliminar/', views.eliminar_cita, name='eliminar_cita'),
    path('<int:cita_id>/estado/', views.cambiar_estado_cita, name='cambiar_estado_cita'),
]
