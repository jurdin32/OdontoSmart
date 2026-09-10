from django.contrib.auth.models import User
from django.test import TestCase

from core.models import Empresa
from facturacion.models import Servicio


class ServicioCatalogoTests(TestCase):
    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Clínica Test', ruc='0999999999001')
        self.user = User.objects.create_user(username='admin_serv', password='12345678')
        self.user.is_superuser = True
        self.user.save()
        profile = self.user.profile
        profile.empresa = self.empresa
        profile.save()
        self.client.force_login(self.user)

    def test_crear_servicio_asigna_empresa(self):
        response = self.client.post('/facturacion/servicios/registrar/', {
            'nombre': 'Limpieza dental',
            'descripcion': 'Profilaxis completa',
            'precio': '25.50',
            'duracion_minutos': '30',
            'activo': 'on',
        })

        self.assertEqual(response.status_code, 302)
        servicio = Servicio.objects.get(nombre='Limpieza dental')
        self.assertEqual(servicio.empresa, self.empresa)
        self.assertEqual(str(servicio.precio), '25.50')
        self.assertTrue(servicio.activo)

    def test_lista_servicios_muestra_los_de_su_empresa(self):
        otra = Empresa.objects.create(nombre='Otra Clínica', ruc='0999999999002')
        Servicio.objects.create(empresa=self.empresa, nombre='Endodoncia', precio=80)
        Servicio.objects.create(empresa=otra, nombre='Ortodoncia', precio=120)

        response = self.client.get('/facturacion/servicios/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Endodoncia')
        self.assertNotContains(response, 'Ortodoncia')

    def test_toggle_servicio_cambia_estado(self):
        servicio = Servicio.objects.create(empresa=self.empresa, nombre='Blanqueamiento', precio=60)

        response = self.client.post(f'/facturacion/servicios/{servicio.id}/toggle/')

        self.assertEqual(response.status_code, 302)
        servicio.refresh_from_db()
        self.assertFalse(servicio.activo)

