from datetime import date, time

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from core.models import Empresa
from pacientes.models import Paciente
from citas.models import Cita


def _paciente(empresa, cedula):
    return Paciente.objects.create(
        empresa=empresa, nombres='Juan', apellidos='Perez',
        cedula=cedula, fecha_nacimiento=date(1990, 1, 1),
        genero='M', telefono='0999999999',
    )


class CitaAislamientoTests(TestCase):
    """Un usuario solo ve/edita/crea citas de su propia empresa."""

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
        self.pac_a = _paciente(self.emp_a, '1111111111')
        self.pac_b = _paciente(self.emp_b, '2222222222')

    def _cita(self, empresa, paciente, motivo):
        return Cita.objects.create(
            empresa=empresa, paciente=paciente,
            fecha=date(2026, 9, 10), hora=time(10, 0), motivo=motivo,
        )

    def test_lista_solo_muestra_citas_de_su_empresa(self):
        self._cita(self.emp_a, self.pac_a, motivo='Control A')
        self._cita(self.emp_b, self.pac_b, motivo='Control B')
        resp = self.client.get(reverse('lista_citas'))
        self.assertContains(resp, 'Control A')
        self.assertNotContains(resp, 'Control B')

    def test_detalle_de_otra_empresa_da_404(self):
        c_b = self._cita(self.emp_b, self.pac_b, motivo='X')
        resp = self.client.get(reverse('detalle_cita', args=[c_b.id]))
        self.assertEqual(resp.status_code, 404)

    def test_registrar_cita_con_paciente_de_otra_empresa_se_rechaza(self):
        data = {'paciente': self.pac_b.id, 'fecha': '2026-09-11',
                'hora': '11:00', 'motivo': 'Test Cross'}
        resp = self.client.post(reverse('registrar_cita'), data)
        self.assertEqual(resp.status_code, 200)  # formulario inválido
        self.assertFalse(Cita.objects.filter(motivo='Test Cross').exists())

    def test_registrar_cita_asigna_empresa_del_usuario(self):
        data = {'paciente': self.pac_a.id, 'fecha': '2026-09-11',
                'hora': '11:00', 'motivo': 'Test OK', 'estado': 'PENDIENTE'}
        resp = self.client.post(reverse('registrar_cita'), data)
        self.assertEqual(resp.status_code, 302)
        c = Cita.objects.get(motivo='Test OK')
        self.assertEqual(c.empresa_id, self.emp_a.id)

