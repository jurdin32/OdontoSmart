from datetime import date

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Empresa
from pacientes.models import Paciente


class PacienteAislamientoTests(TestCase):
    """Un usuario solo ve/edita pacientes de su propia empresa."""

    def setUp(self):
        self.emp_a = Empresa.objects.create(
            nombre='Clinica A', ruc='1111111111001', activo=True
        )
        self.emp_b = Empresa.objects.create(
            nombre='Clinica B', ruc='2222222222001', activo=True
        )
        self.user_a = User.objects.create_user(
            username='user_a', password='clave12345', is_superuser=True
        )
        self.user_a.profile.empresa = self.emp_a
        self.user_a.profile.save()
        self.client.login(username='user_a', password='clave12345')

    def _paciente(self, empresa, cedula):
        return Paciente.objects.create(
            empresa=empresa, nombres='Juan', apellidos='Perez',
            cedula=cedula, fecha_nacimiento=date(1990, 1, 1),
            genero='M', telefono='0999999999',
        )

    def test_lista_solo_muestra_empresa_del_usuario(self):
        p_a = self._paciente(self.emp_a, '1111111111')
        self._paciente(self.emp_b, '2222222222')
        resp = self.client.get(reverse('lista_pacientes'))
        self.assertContains(resp, p_a.cedula)
        self.assertNotContains(resp, '2222222222')

    def test_detalle_de_otra_empresa_da_404(self):
        p_b = self._paciente(self.emp_b, '2222222222')
        resp = self.client.get(reverse('detalle_paciente', args=[p_b.id]))
        self.assertEqual(resp.status_code, 404)

    def test_editar_de_otra_empresa_da_404(self):
        p_b = self._paciente(self.emp_b, '2222222222')
        resp = self.client.get(reverse('editar_paciente', args=[p_b.id]))
        self.assertEqual(resp.status_code, 404)

    def test_registrar_asigna_empresa_del_usuario(self):
        data = {
            'nombres': 'Ana', 'apellidos': 'Gomez', 'cedula': '3333333333',
            'fecha_nacimiento': '1992-02-02', 'genero': 'F',
            'telefono': '0888888888',
        }
        resp = self.client.post(reverse('registrar_paciente'), data)
        self.assertEqual(resp.status_code, 302)
        p = Paciente.objects.get(cedula='3333333333')
        self.assertEqual(p.empresa_id, self.emp_a.id)

