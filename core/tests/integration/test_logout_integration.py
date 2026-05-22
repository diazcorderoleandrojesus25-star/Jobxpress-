from django.test import TransactionTestCase
from django.utils import timezone

from core.models import Rol, Usuario
from core.tests.integration._db_support import ensure_auth_tables


class LogoutIntegrationTestCase(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_auth_tables()

    def test_logout_flushes_session_and_redirects_home(self):
        rol_cliente, _ = Rol.objects.get_or_create(rol="ROLE_CLIENTE")
        user = Usuario.objects.create(
            nombre="Carlos",
            apellido="Sesion",
            email="carlos.sesion@jobxpress.com",
            telefono="3012345678",
            contrasena="temporal",
            direccion="Carrera 15 # 40-10",
            activo=1,
            rol=rol_cliente,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )

        session = self.client.session
        session["usuario_id"] = user.id_usuario
        session.save()

        response = self.client.get("/logout")

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, "/")
        self.assertIsNone(self.client.session.get("usuario_id"))
