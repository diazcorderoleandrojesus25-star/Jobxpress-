import json
from datetime import date

from django.test import TransactionTestCase
from django.utils import timezone

from core.models import (
    Categoria,
    ClienteContratacion,
    Contratacion,
    Prestador,
    Rol,
    Servicio,
    Usuario,
)
from core.tests.integration._db_support import ensure_auth_tables, ensure_tables
from core.view_modules.common import _hash_password


class ClienteSolicitudIntegrationTestCase(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_auth_tables()
        ensure_tables(Prestador, Categoria, Servicio, Contratacion, ClienteContratacion)

    def setUp(self):
        rol_cliente, _ = Rol.objects.get_or_create(rol="ROLE_CLIENTE")
        rol_prestador, _ = Rol.objects.get_or_create(rol="ROLE_PRESTADOR")

        self.cliente = Usuario.objects.create(
            nombre="Laura",
            apellido="Cliente",
            email="laura.cliente@jobxpress.com",
            telefono="3001112233",
            contrasena=_hash_password("Cliente123!"),
            direccion="Calle 50 # 20-10",
            activo=1,
            rol=rol_cliente,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        usuario_prestador = Usuario.objects.create(
            nombre="Pedro",
            apellido="Prestador",
            email="pedro.prestador@jobxpress.com",
            telefono="3012223344",
            contrasena=_hash_password("Prestador123!"),
            direccion="Carrera 12 # 7-40",
            activo=1,
            rol=rol_prestador,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        self.prestador = Prestador.objects.create(
            usuario=usuario_prestador,
            descripcion="Tecnico con experiencia",
            dias_atencion="Lunes, Martes",
            horario_atencion="08:00 - 17:00",
        )
        self.categoria = Categoria.objects.create(nombre="Plomeria", activo=1)
        self.servicio = Servicio.objects.create(
            nombre="Plomeria residencial",
            descripcion="Reparacion de fugas",
            precio_min=50000,
            precio_max=120000,
            activo=1,
            prestador=self.prestador,
            categoria=self.categoria,
        )

        session = self.client.session
        session["usuario_id"] = self.cliente.id_usuario
        session.save()

    def test_cliente_solicitud_creates_contratacion_and_link(self):
        payload = {
            "prestador_id": self.prestador.id_prestador,
            "servicio_id": self.servicio.id_servicio,
            "servicio": "Plomeria",
            "fecha": date.today().isoformat(),
            "hora": "10:30",
            "monto": "85000",
            "direccion": "Calle 80 # 10-20",
            "descripcion": "Revisar una fuga en cocina",
        }

        response = self.client.post(
            "/cliente/solicitud",
            data=json.dumps(payload),
            content_type="application/json",
            secure=True,
        )

        self.assertEqual(response.status_code, 201)
        id_contratacion = response.json().get("idContratacion")
        self.assertIsNotNone(id_contratacion)

        contratacion = Contratacion.objects.get(id_contratacion=id_contratacion)
        self.assertEqual(contratacion.estado, "Pendiente")
        self.assertEqual(contratacion.prestador_id, self.prestador.id_prestador)
        self.assertEqual(contratacion.servicio_id, self.servicio.id_servicio)

        observacion = json.loads(contratacion.observacion or "{}")
        self.assertEqual(observacion.get("hora"), payload["hora"])
        self.assertEqual(observacion.get("monto"), payload["monto"])
        self.assertEqual(observacion.get("direccion"), payload["direccion"])
        self.assertEqual(observacion.get("descripcion"), payload["descripcion"])

        self.assertTrue(
            ClienteContratacion.objects.filter(
                cliente=self.cliente,
                contratacion=contratacion,
            ).exists()
        )

    def test_cliente_historial_muestra_rechazo_como_respuesta_real(self):
        contratacion = Contratacion.objects.create(
            fecha=date.today(),
            fecha_solicitud=date.today(),
            estado="Rechazado",
            observacion='{"hora":"10:30","monto":"85000","direccion":"Calle 80 # 10-20","descripcion":"Revisar una fuga en cocina"}',
            prestador=self.prestador,
            servicio=self.servicio,
        )
        ClienteContratacion.objects.create(cliente=self.cliente, contratacion=contratacion)

        response = self.client.get("/cliente/historial", secure=True, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '"respuestaPrestador": "rechazado"')
