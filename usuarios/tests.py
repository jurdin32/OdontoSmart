from django.contrib.auth.models import User
from django.test import TestCase

from core.models import Empresa
from medicos.models import Medico
from usuarios.views import _normalizar_nombre_usuario, _vincular_medico


class UsuarioNombreSeguroTests(TestCase):
    def test_normalizar_nombre_usuario_con_campos_vacios(self):
        user = User(username='admin')
        user.first_name = '   '
        user.last_name = ''

        nombres, apellidos = _normalizar_nombre_usuario(user)

        self.assertEqual(nombres, 'admin')
        self.assertEqual(apellidos, 'admin')

    def test_vincular_medico_no_falla_si_falta_nombres(self):
        empresa = Empresa.objects.create(nombre='Clínica Test', ruc='0999999999001')
        user = User.objects.create_user(username='admin_sin_nombres', password='12345678')
        user.first_name = '   '
        user.last_name = ''
        user.save(update_fields=['first_name', 'last_name'])

        _vincular_medico(user, empresa)

        medico = Medico.objects.get(user=user)
        self.assertEqual(medico.nombres, 'admin_sin_nombres')
        self.assertEqual(medico.apellidos, 'admin_sin_nombres')

    def test_dashboard_no_falla_si_hay_actividad_sin_usuario(self):
        user = User.objects.create_user(username='admin_dashboard', password='12345678')
        user.first_name = 'Ana'
        user.last_name = 'Pérez'
        user.save(update_fields=['first_name', 'last_name'])

        from usuarios.models import ActivityLog
        ActivityLog.objects.create(
            empresa=None,
            usuario=None,
            accion='LOGIN',
            modelo='Usuario',
            descripcion='Inicio de sesión - sistema'
        )

        self.client.force_login(user)
        response = self.client.get('/dashboard/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sistema')
