from django.test import TestCase, RequestFactory

from core.models import Empresa
from core.tenant import EmpresaMiddleware, get_empresa


class ClinicaUnicaTests(TestCase):
    """Modo clínica única: la app trabaja siempre con la misma empresa
    (la primera activa) e ignora cualquier parámetro de tenant."""

    def setUp(self):
        self.emp = Empresa.objects.create(
            nombre='Clínica Única', ruc='1111111111001', activo=True
        )
        self.factory = RequestFactory()

    def _empresa_de_request(self, query=''):
        req = self.factory.get('/dashboard/' + query)
        req.session = {}
        EmpresaMiddleware(lambda r: None).process_request(req)
        return getattr(req, 'empresa', None)

    def test_middleware_asigna_la_clinica_unica(self):
        self.assertEqual(self._empresa_de_request().id, self.emp.id)

    def test_parametro_empresa_id_es_ignorado(self):
        self.assertEqual(self._empresa_de_request('?empresa_id=999999').id, self.emp.id)

    def test_get_empresa_con_request_devuelve_la_clinica(self):
        req = self.factory.get('/dashboard/')
        self.assertEqual(get_empresa(req).id, self.emp.id)

    def test_get_empresa_sin_request_devuelve_la_clinica(self):
        self.assertEqual(get_empresa().id, self.emp.id)

    def test_no_usa_una_segunda_empresa(self):
        Empresa.objects.create(nombre='Otra', ruc='2222222222001', activo=True)
        self.assertEqual(get_empresa().id, self.emp.id)

