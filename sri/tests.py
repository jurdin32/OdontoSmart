"""Tests del registro de la respuesta del SRI."""

from django.test import TestCase
from django.utils import timezone

from core.models import Empresa
from sri.models import SriDocumento, SriEmpresaConfig


class MarcarAutorizadoTests(TestCase):
    """`marcar_autorizado()` debe guardar la respuesta completa del SRI."""

    def setUp(self):
        self.empresa = Empresa.objects.create(nombre='Clínica Aut', ruc='0999999999004')
        self.config = SriEmpresaConfig.objects.create(
            empresa=self.empresa, ruc='0999999999004',
            razon_social='Clínica Aut', ambiente='1',
        )
        self.doc = SriDocumento.objects.create(
            empresa_config=self.config, tipo='01',
            clave_acceso='0909202601070388669700110010010000012003304540199',
            numero_documento='001-001-000000199', ambiente='1',
            estado='ENVIADO',
        )

    def test_guarda_fecha_y_numero_de_autorizacion(self):
        self.doc.marcar_autorizado({
            'estado': 'AUTORIZADO',
            'fecha_autorizacion': '2026-09-09T15:30:00-05:00',
            'xml_autorizado': '<autorizacion/>',
            'mensajes': [],
        }, self.doc.clave_acceso)

        self.assertEqual(self.doc.estado, 'AUTORIZADO')
        self.assertEqual(self.doc.numero_autorizacion, self.doc.clave_acceso)
        self.assertEqual(self.doc.xml_autorizado, '<autorizacion/>')
        self.assertIsNotNone(self.doc.fecha_autorizacion)
        self.assertEqual(self.doc.fecha_autorizacion.year, 2026)
        self.assertEqual(self.doc.fecha_autorizacion.hour, 15)
        self.assertTrue(self.doc.autorizado)

    def test_numero_de_autorizacion_del_sri_tiene_prioridad(self):
        self.doc.marcar_autorizado({
            'estado': 'AUTORIZADO',
            'numero_autorizacion': 'NUM-SRI-123',
        }, 'clave-de-acceso')

        self.assertEqual(self.doc.numero_autorizacion, 'NUM-SRI-123')

    def test_sin_fecha_del_sri_usa_el_momento_de_la_consulta(self):
        antes = timezone.now()

        self.doc.marcar_autorizado({'estado': 'AUTORIZADO'}, 'clave-x')

        self.assertGreaterEqual(self.doc.fecha_autorizacion, antes)
        self.assertEqual(self.doc.numero_autorizacion, 'clave-x')

    def test_guarda_los_mensajes_cuando_los_hay(self):
        self.doc.marcar_autorizado({
            'estado': 'AUTORIZADO',
            'mensajes': [{'identificador': '1', 'mensaje': 'AUTORIZADO', 'tipo': 'INFORMATIVO'}],
        })

        self.assertEqual(len(self.doc.mensajes), 1)
        self.assertEqual(self.doc.mensajes[0]['tipo'], 'INFORMATIVO')

    def test_guarda_el_archivo_xml_autorizado(self):
        self.doc.marcar_autorizado({
            'estado': 'AUTORIZADO',
            'xml_autorizado': '<autorizacion><comprobante/></autorizacion>',
        })

        self.doc.guardar_xml_autorizado()

        self.assertTrue(self.doc.archivo_xml_autorizado)
        self.assertTrue(self.doc.archivo_xml_autorizado.name.endswith('.xml'))

    def test_sin_xml_no_crea_archivo(self):
        self.doc.marcar_autorizado({'estado': 'AUTORIZADO'})

        self.assertEqual(self.doc.guardar_xml_autorizado(), '')
        self.assertFalse(self.doc.archivo_xml_autorizado)

# Create your tests here.
