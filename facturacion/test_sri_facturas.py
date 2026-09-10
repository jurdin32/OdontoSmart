"""Tests de la respuesta del SRI visible en la lista de facturas."""

from datetime import date

from django.contrib.auth.models import User
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from core.models import Empresa
from facturacion.models import Factura
from pacientes.models import Paciente
from sri.models import SriDocumento, SriEmpresaConfig

MODELO = 'facturacion.factura'


class RespuestaSriEnListaTests(TestCase):
    """La lista debe mostrar si el SRI autorizó la factura."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Clínica SRI', ruc='0999999999003')
        self.user = User.objects.create_user(username='admin_sri', password='12345678')
        self.user.is_superuser = True
        self.user.save()
        profile = self.user.profile
        profile.empresa = self.empresa
        profile.save()
        self.client.force_login(self.user)

        self.paciente = Paciente.objects.create(
            empresa=self.empresa,
            nombres='Ana', apellidos='Pérez', cedula='1712345678',
            fecha_nacimiento=date(1990, 5, 5), genero='F', telefono='0999999999',
        )
        self.config = SriEmpresaConfig.objects.create(
            empresa=self.empresa, ruc='0999999999003',
            razon_social='Clínica SRI', ambiente='1',
        )

    def _factura(self, numero):
        return Factura.objects.create(
            empresa=self.empresa, numero=numero, paciente=self.paciente,
            items=[{'descripcion': 'Consulta', 'cantidad': 1, 'precio_unitario': 20}],
        )

    def _documento(self, factura, **kwargs):
        datos = {
            'empresa_config': self.config,
            'tipo': '01',
            'clave_acceso': '09092026010703886697001100100100000' + str(factura.id).zfill(4),
            'numero_documento': factura.numero,
            'factura_origen_id': factura.id,
            'factura_origen_modelo': MODELO,
            'ambiente': '1',
        }
        datos.update(kwargs)
        return SriDocumento.objects.create(**datos)

    def test_factura_encuentra_documento_sri_guardado_por_el_servicio(self):
        """Regresión: el SRI guarda 'facturacion.factura', no 'Factura'."""
        factura = self._factura('FAC-SRI-1')
        self._documento(
            factura, estado='AUTORIZADO', numero_autorizacion='1234567890',
            fecha_autorizacion=timezone.now(),
        )

        self.assertIsNotNone(factura.sri_documento)
        self.assertTrue(factura.sri_autorizado)
        self.assertEqual(factura.sri_estado_codigo, 'AUTORIZADO')
        self.assertEqual(factura.sri_numero_autorizacion, '1234567890')

    def test_lista_muestra_estado_y_numero_de_autorizacion(self):
        factura = self._factura('FAC-SRI-2')
        self._documento(
            factura, estado='AUTORIZADO', numero_autorizacion='0987654321',
            fecha_autorizacion=timezone.now(),
        )

        response = self.client.get('/facturacion/facturas/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Autorizado')
        self.assertContains(response, '0987654321')

    def test_lista_muestra_mensaje_de_error_del_sri(self):
        factura = self._factura('FAC-SRI-3')
        self._documento(
            factura, estado='ERROR',
            mensajes=[{
                'identificador': '39',
                'mensaje': 'FIRMA INVALIDA',
                'tipo': 'ERROR',
                'informacionAdicional': 'La firma es invalida',
            }],
        )

        response = self.client.get('/facturacion/facturas/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'FIRMA INVALIDA')

    def test_lista_marca_factura_sin_enviar(self):
        self._factura('FAC-SRI-4')

        response = self.client.get('/facturacion/facturas/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Sin enviar')

    def test_filtro_sri_autorizado_excluye_las_no_enviadas(self):
        autorizada = self._factura('FAC-SRI-5')
        self._factura('FAC-SRI-6')
        self._documento(autorizada, estado='AUTORIZADO', numero_autorizacion='111')

        response = self.client.get('/facturacion/facturas/?sri=AUTORIZADO')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'FAC-SRI-5')
        self.assertNotContains(response, 'FAC-SRI-6')

    def test_filtro_sri_sin_enviar_excluye_las_autorizadas(self):
        autorizada = self._factura('FAC-SRI-7')
        self._factura('FAC-SRI-8')
        self._documento(autorizada, estado='AUTORIZADO', numero_autorizacion='222')

        response = self.client.get('/facturacion/facturas/?sri=SIN_ENVIAR')

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'FAC-SRI-7')
        self.assertContains(response, 'FAC-SRI-8')

    def test_filtro_sri_rechazado_incluye_errores(self):
        con_error = self._factura('FAC-SRI-9')
        self._factura('FAC-SRI-10')
        self._documento(con_error, estado='ERROR', mensajes=[{'mensaje': 'X', 'tipo': 'ERROR'}])

        response = self.client.get('/facturacion/facturas/?sri=RECHAZADO')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'FAC-SRI-9')
        self.assertNotContains(response, 'FAC-SRI-10')

    def test_lista_incluye_el_json_de_respuesta_del_sri(self):
        """El visor JSON se alimenta de un bloque json_script con la respuesta."""
        factura = self._factura('FAC-SRI-11')
        self._documento(
            factura, estado='AUTORIZADO', numero_autorizacion='ABC123',
            fecha_autorizacion=timezone.now(),
        )

        response = self.client.get('/facturacion/facturas/')
        html = response.content.decode()

        self.assertIn('id="sriRespuestasData"', html)
        self.assertIn('btn-sri-json', html)
        self.assertIn('ABC123', html)

        import json as _json
        payload = _json.loads(
            html.split('id="sriRespuestasData" type="application/json">')[1].split('</script>')[0]
        )
        self.assertEqual(payload[str(factura.id)]['estado'], 'AUTORIZADO')
        self.assertEqual(payload[str(factura.id)]['numero_autorizacion'], 'ABC123')

    def test_respuesta_sri_json_vacia_si_no_se_envio(self):
        factura = self._factura('FAC-SRI-12')

        self.assertEqual(factura.respuesta_sri_json(), {})

    def test_lista_no_hace_consultas_por_factura(self):
        """El estado del SRI se carga en una sola consulta (sin N+1)."""
        factura = self._factura('FAC-SRI-N0')
        self._documento(factura, estado='AUTORIZADO', numero_autorizacion='0')
        with CaptureQueriesContext(connection) as una_factura:
            self.client.get('/facturacion/facturas/')

        for i in range(1, 5):
            extra = self._factura(f'FAC-SRI-N{i}')
            self._documento(extra, estado='AUTORIZADO', numero_autorizacion=str(i))

        with CaptureQueriesContext(connection) as cinco_facturas:
            self.client.get('/facturacion/facturas/')

        self.assertEqual(len(una_factura), len(cinco_facturas))
