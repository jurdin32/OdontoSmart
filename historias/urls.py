from django.urls import path
from . import views

urlpatterns = [
    path('paciente/<int:paciente_id>/', views.historia_view, name='historia'),
    path('paciente/<int:paciente_id>/odontograma/', views.odontograma_view, name='odontograma'),
    path('paciente/<int:paciente_id>/odontograma/infantil/', views.odontograma_infantil_view, name='odontograma_infantil'),
    path('paciente/<int:paciente_id>/evolucion/nueva/', views.nueva_evolucion, name='nueva_evolucion'),
    path('evolucion/<int:evolucion_id>/editar/', views.editar_evolucion, name='editar_evolucion'),
    path('evolucion/<int:evolucion_id>/eliminar/', views.eliminar_evolucion, name='eliminar_evolucion'),
    path('evolucion/<int:evolucion_id>/imprimir/', views.imprimir_consentimiento, name='imprimir_consentimiento'),
]
