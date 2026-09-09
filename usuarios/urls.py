from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard_view, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('reset-password/', views.reset_password_view, name='reset_password'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('buscar/', views.buscar_view, name='buscar'),
    # Gestión de usuarios
    path('usuarios/', views.lista_usuarios, name='lista_usuarios'),
    path('usuarios/registrar/', views.registrar_usuario, name='registrar_usuario'),
    path('usuarios/<int:user_id>/editar/', views.editar_usuario, name='editar_usuario'),
    path('usuarios/<int:user_id>/permisos/', views.asignar_permisos, name='asignar_permisos'),
    path('usuarios/<int:user_id>/toggle-activo/', views.toggle_usuario_activo, name='toggle_usuario_activo'),
    # Vincular médicos sin usuario
    path('usuarios/medicos-sin-usuario/', views.medicos_sin_usuario, name='medicos_sin_usuario'),
    path('usuarios/crear-desde-medico/<int:medico_id>/', views.crear_usuario_desde_medico, name='crear_usuario_desde_medico'),
    # Gestión de roles
    path('roles/', views.lista_roles, name='lista_roles'),
    path('roles/crear/', views.crear_rol, name='crear_rol'),
    path('roles/<int:rol_id>/editar/', views.editar_rol, name='editar_rol'),
    path('roles/<int:rol_id>/eliminar/', views.eliminar_rol, name='eliminar_rol'),
    path('roles/<int:rol_id>/permisos/', views.permisos_rol, name='permisos_rol'),
    # Gestión de permisos
    path('permisos/', views.lista_permisos, name='lista_permisos'),
    path('permisos/crear/', views.crear_permiso, name='crear_permiso'),
    path('permisos/<int:permiso_id>/editar/', views.editar_permiso, name='editar_permiso'),
    path('permisos/<int:permiso_id>/eliminar/', views.eliminar_permiso, name='eliminar_permiso'),
]
