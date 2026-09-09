from django.urls import path
from . import views

urlpatterns = [
    path('', views.lista_medicos, name='lista_medicos'),
    path('registrar/', views.registrar_medico, name='registrar_medico'),
    path('<int:medico_id>/', views.detalle_medico, name='detalle_medico'),
    path('<int:medico_id>/editar/', views.editar_medico, name='editar_medico'),
    path('<int:medico_id>/eliminar/', views.eliminar_medico, name='eliminar_medico'),
]
