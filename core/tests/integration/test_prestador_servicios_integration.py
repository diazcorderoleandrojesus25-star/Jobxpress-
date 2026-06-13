from django.test import TransactionTestCase
from django.utils import timezone

from core.models import (
    Categoria,
    Prestador,
    PrestadorCategoria,
    Rol,
    Servicio,
    Usuario,
)
from core.tests.integration._db_support import ensure_auth_tables, ensure_tables
from core.view_modules.common import _hash_password


class PrestadorServiciosIntegrationTestCase(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_auth_tables()
        ensure_tables(Categoria, Prestador, PrestadorCategoria, Servicio)

    def setUp(self):
        self.rol_prestador, _ = Rol.objects.get_or_create(rol="ROLE_PRESTADOR")
        self.categoria = Categoria.objects.create(nombre="Plomeria", activo=1)
        self.servicio = Servicio.objects.create(
            nombre="Plomeria residencial",
            descripcion="Reparacion de fugas",
            precio_min=50000,
            precio_max=120000,
            activo=1,
            prestador=None,
            categoria=self.categoria,
        )

    def test_registro_prestador_no_crea_servicio_duplicado(self):
        total_antes = Servicio.objects.count()

        response = self.client.post(
            "/registro",
            {
                "nombre": "Pedro",
                "apellido": "Prestador",
                "email": "pedro.nuevo@jobxpress.com",
                "telefono": "3012223344",
                "direccion": "Carrera 12 # 7-40",
                "contrasena": "Prestador123!",
                "contrasena_confirmation": "Prestador123!",
                "id_rol": str(self.rol_prestador.id_rol),
                "servicio_id": str(self.servicio.id_servicio),
                "prestador_dias": ["Lun", "Mar"],
                "prestador_hora_inicio": "08:00 AM",
                "prestador_hora_fin": "05:00 PM",
                "prestador_descripcion": "Tecnico con experiencia en reparaciones.",
            },
            secure=True,
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Prestador.objects.filter(usuario__email="pedro.nuevo@jobxpress.com").exists())
        self.assertEqual(Servicio.objects.count(), total_antes)

        prestador = Prestador.objects.get(usuario__email="pedro.nuevo@jobxpress.com")
        self.assertTrue(
            PrestadorCategoria.objects.filter(
                prestador=prestador,
                categoria=self.categoria,
            ).exists()
        )
        self.assertTrue(Servicio.objects.filter(prestador=prestador, id_servicio=self.servicio.id_servicio).exists())

        session = self.client.session
        session["usuario_id"] = prestador.usuario.id_usuario
        session.save()

        servicio_page = self.client.get("/prestador/servicioPrestador", secure=True, follow=True)
        self.assertEqual(servicio_page.status_code, 200)
        self.assertContains(servicio_page, self.servicio.nombre)
        self.assertNotContains(servicio_page, "No tienes servicios registrados.")

    def test_prestador_home_no_crea_servicio_duplicado(self):
        usuario = Usuario.objects.create(
            nombre="Paula",
            apellido="Prestadora",
            email="paula.prestadora@jobxpress.com",
            telefono="3012223344",
            contrasena=_hash_password("Prestador123!"),
            direccion="Carrera 12 # 7-40",
            activo=1,
            rol=self.rol_prestador,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        prestador = Prestador.objects.create(
            usuario=usuario,
            descripcion="Tecnica con experiencia",
            dias_atencion="Lun, Mar",
            horario_atencion="08:00 AM - 05:00 PM",
        )
        PrestadorCategoria.objects.create(prestador=prestador, categoria=self.categoria)
        total_antes = Servicio.objects.count()

        session = self.client.session
        session["usuario_id"] = usuario.id_usuario
        session.save()

        response = self.client.get("/prestador/home", secure=True, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Servicio.objects.count(), total_antes)

    def test_servicioprestador_no_inventa_servicio_para_prestador_nuevo(self):
        usuario = Usuario.objects.create(
            nombre="Laura",
            apellido="Prestadora",
            email="laura.prestadora@jobxpress.com",
            telefono="3012223344",
            contrasena=_hash_password("Prestador123!"),
            direccion="Carrera 12 # 7-40",
            activo=1,
            rol=self.rol_prestador,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        prestador = Prestador.objects.create(
            usuario=usuario,
            descripcion="Tecnica con experiencia",
            dias_atencion="Lun, Mar",
            horario_atencion="08:00 AM - 05:00 PM",
        )
        PrestadorCategoria.objects.create(prestador=prestador, categoria=self.categoria)

        session = self.client.session
        session["usuario_id"] = usuario.id_usuario
        session.save()

        response = self.client.get("/prestador/servicioPrestador", secure=True, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No tienes servicios registrados.")
