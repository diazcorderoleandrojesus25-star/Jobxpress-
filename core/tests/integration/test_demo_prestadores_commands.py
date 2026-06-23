from io import StringIO

from django.core.management import call_command
from django.test import TransactionTestCase

from core.models import Categoria, Prestador, PrestadorCategoria, Rol, Servicio, Usuario
from core.tests.integration._db_support import ensure_auth_tables, ensure_tables
from core.view_modules.common import _hash_password


class DemoPrestadoresCommandsTestCase(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_auth_tables()
        ensure_tables(Categoria, Prestador, PrestadorCategoria, Servicio)

    def test_cleanup_extra_demo_services_removes_demo_users_and_services(self):
        rol_admin, _ = Rol.objects.get_or_create(id_rol=1, defaults={"rol": "ROLE_ADMIN"})
        rol_prestador, _ = Rol.objects.get_or_create(id_rol=3, defaults={"rol": "ROLE_PRESTADOR"})
        categoria = Categoria.objects.create(nombre="Plomeria", activo=1)

        admin = Usuario.objects.create(
            nombre="Admin",
            apellido="Base",
            email="admin@jobxpress.local",
            telefono="3000000000",
            contrasena=_hash_password("Admin123!"),
            direccion="Calle 1 # 1-1",
            activo=1,
            rol=rol_admin,
        )

        demo_user = Usuario.objects.create(
            nombre="Demo",
            apellido="Prestador",
            email="extra-prestador-01-1@jobxpress.local",
            telefono="3000000001",
            contrasena=_hash_password("Prestador123!"),
            direccion="Calle 10 # 20-30",
            activo=1,
            rol=rol_prestador,
        )
        demo_prestador = Prestador.objects.create(
            usuario=demo_user,
            descripcion="Demo",
            dias_atencion="Lun a Vie",
            horario_atencion="8:00am - 5:00pm",
        )
        Servicio.objects.create(
            nombre="Plomeria residual",
            descripcion="Servicio de prueba",
            precio_min=50000,
            precio_max=120000,
            activo=1,
            prestador=demo_prestador,
            categoria=categoria,
        )

        call_command("cleanup_extra_demo_services", stdout=StringIO())

        self.assertTrue(Usuario.objects.filter(pk=admin.pk).exists())
        self.assertFalse(Usuario.objects.filter(pk=demo_user.pk).exists())
        self.assertFalse(Servicio.objects.filter(prestador=demo_prestador).exists())

    def test_restore_catalog_services_deja_solo_catalogo_base(self):
        rol_prestador, _ = Rol.objects.get_or_create(id_rol=3, defaults={"rol": "ROLE_PRESTADOR"})
        categoria = Categoria.objects.create(nombre="Plomeria", activo=1)
        usuario = Usuario.objects.create(
            nombre="Luis",
            apellido="Demo",
            email="luis.demo@jobxpress.com",
            telefono="3000000002",
            contrasena=_hash_password("Prestador123!"),
            direccion="Calle 2 # 2-2",
            activo=1,
            rol=rol_prestador,
        )
        prestador = Prestador.objects.create(
            usuario=usuario,
            descripcion="Demo",
            dias_atencion="Lun a Vie",
            horario_atencion="8:00am - 5:00pm",
        )

        base = Servicio.objects.create(
            id_servicio=1,
            nombre="Plomeria residencial",
            descripcion="Servicio base",
            precio_min=50000,
            precio_max=120000,
            activo=1,
            prestador=prestador,
            categoria=categoria,
        )
        extra = Servicio.objects.create(
            nombre="Plomeria residencial",
            descripcion="Servicio duplicado",
            precio_min=55000,
            precio_max=130000,
            activo=1,
            prestador=prestador,
            categoria=categoria,
        )

        call_command("restore_catalog_services", stdout=StringIO())

        base.refresh_from_db()
        self.assertIsNone(base.prestador_id)
        self.assertTrue(Servicio.objects.filter(pk=base.pk).exists())
        self.assertFalse(Servicio.objects.filter(pk=extra.pk).exists())
