from django.urls import path
from . import api_views, views

urlpatterns = [
    # API de locks (concurrencia)
    path('lock/renew/', api_views.lock_renew, name='lock_renew'),
    path('lock/check/', api_views.lock_check, name='lock_check'),
    path('lock/release/', api_views.lock_release, name='lock_release'),

    # Gestión de tareas en segundo plano
    path('tareas/', views.tareas_list, name='tareas_list'),
    path('tareas/<str:tarea>/ejecutar/', views.ejecutar_tarea, name='ejecutar_tarea'),
    path('tareas/log/<int:log_id>/eliminar/', views.eliminar_log, name='eliminar_log_tarea'),

    # Configuración de empresa (multi-tenant)
    path('configuracion/', views.configuracion_empresa, name='configuracion_empresa'),
]
