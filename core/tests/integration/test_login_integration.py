from django.test import TransactionTestCase
from django.utils import timezone

from core.models import Rol, Usuario
from core.tests.integration._db_support import ensure_auth_tables
from core.view_modules.common import _hash_password


class LoginIntegrationTestCase(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_auth_tables()

    def test_login_redirects_cliente_and_stores_session(self):
        rol_cliente, _ = Rol.objects.get_or_create(rol="ROLE_CLIENTE")
        user = Usuario.objects.create(
            nombre="Ana",
            apellido="Cliente",
            email="cliente@jobxpress.com",
            telefono="3001234567",
            contrasena=_hash_password("Segura123!"),
            direccion="Calle 10 # 20-30",
            activo=1,
            rol=rol_cliente,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        response = self.client.post(
            "/login",
            {"username": "cliente@jobxpress.com", "password": "Segura123!"},
            secure=True,
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/cliente/home")
        self.assertEqual(self.client.session.get("usuario_id"), user.id_usuario)

    def test_login_page_disables_cache_for_credentials(self):
        response = self.client.get("/login", secure=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn("no-store", response["Cache-Control"])
        self.assertIn("no-cache", response["Pragma"])
        self.assertEqual(response["Expires"], "0")
