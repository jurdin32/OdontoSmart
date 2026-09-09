from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User

from core.models import Empresa
from core.tenant import EmpresaMiddleware, get_empresa
from usuarios.models import Profile


class TenantAislamientoTests(TestCase):
    """Aislamiento multi-tenant: la empresa de un usuario autenticado
    no puede ser suplantada vía '?empresa_id='."""

    def setUp(self):
        self.emp_a = Empresa.objects.create(
            nombre='Clinica A', ruc='1111111111001', activo=True
        )
        self.emp_b = Empresa.objects.create(
            nombre='Clinica B', ruc='2222222222001', activo=True
        )
        self.user_a = User.objects.create_user(
            username='user_a', password='clave12345'
        )
        # El post_save de User crea el Profile automáticamente: lo asignamos
        profile = self.user_a.profile
        profile.empresa = self.emp_a
        profile.save()
        self.factory = RequestFactory()

    def _request_con_empresa(self, authed, query=''):
        req = self.factory.get('/dashboard/' + query)
        req.session = {}
        if authed:
            req.user = self.user_a
        EmpresaMiddleware(lambda r: None).process_request(req)
        return getattr(req, 'empresa', None)

    def test_usuario_autenticado_no_puede_suplantar_empresa_por_get(self):
        # Con una empresa B real en '?empresa_id' debe quedar en su empresa A
        empresa = self._request_con_empresa(True, f'?empresa_id={self.emp_b.id}')
        self.assertEqual(empresa.id, self.emp_a.id)

    def test_usuario_autenticado_con_empresa_inexistente_queda_en_su_perfil(self):
        empresa = self._request_con_empresa(True, '?empresa_id=999999')
        self.assertEqual(empresa.id, self.emp_a.id)

    def test_usuario_autenticado_sin_query_usa_su_perfil(self):
        empresa = self._request_con_empresa(True)
        self.assertEqual(empresa.id, self.emp_a.id)

    def test_anonimo_puede_elegir_empresa_en_login(self):
        # En desarrollo el login anónimo usa '?empresa_id' para elegir tenant
        empresa = self._request_con_empresa(False, f'?empresa_id={self.emp_b.id}')
        self.assertEqual(empresa.id, self.emp_b.id)

    def test_anonimo_con_empresa_inexistente_no_tiene_empresa(self):
        empresa = self._request_con_empresa(False, '?empresa_id=999999')
        self.assertIsNone(empresa)

    def test_get_empresa_fallback_sin_middleware(self):
        # Si el middleware no corrió, get_empresa cae al perfil del usuario
        req = self.factory.get('/dashboard/')
        req.user = self.user_a
        self.assertEqual(get_empresa(req).id, self.emp_a.id)

