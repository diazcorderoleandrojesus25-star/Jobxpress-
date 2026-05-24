import json
from datetime import date

from django.test import TransactionTestCase
from django.utils import timezone

from core.models import (
    Calificacion,
    Categoria,
    ClienteCalificacion,
    ClienteContratacion,
    Contratacion,
    Prestador,
    Rol,
    Servicio,
    Usuario,
)
from core.tests.integration._db_support import ensure_auth_tables, ensure_tables
from core.view_modules.common import _hash_password


class CalificacionesIntegrationTestCase(TransactionTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        ensure_auth_tables()
        ensure_tables(
            Prestador,
            Categoria,
            Servicio,
            Contratacion,
            ClienteContratacion,
            Calificacion,
            ClienteCalificacion,
        )

    def setUp(self):
        rol_cliente, _ = Rol.objects.get_or_create(rol="ROLE_CLIENTE")
        rol_prestador, _ = Rol.objects.get_or_create(rol="ROLE_PRESTADOR")

        self.cliente = Usuario.objects.create(
            nombre="Maria",
            apellido="Cliente",
            email="maria.califica@jobxpress.com",
            telefono="3021112233",
            contrasena=_hash_password("Cliente123!"),
            direccion="Calle 45 # 18-70",
            activo=1,
            rol=rol_cliente,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        usuario_prestador = Usuario.objects.create(
            nombre="Jorge",
            apellido="Prestador",
            email="jorge.servicio@jobxpress.com",
            telefono="3032223344",
            contrasena=_hash_password("Prestador123!"),
            direccion="Carrera 22 # 30-11",
            activo=1,
            rol=rol_prestador,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        self.prestador = Prestador.objects.create(
            usuario=usuario_prestador,
            descripcion="Especialista en mantenimiento",
            dias_atencion="Lunes, Miercoles",
            horario_atencion="09:00 - 18:00",
        )
        categoria = Categoria.objects.create(nombre="Electricidad", activo=1)
        servicio = Servicio.objects.create(
            nombre="Instalacion electrica",
            descripcion="Soporte en instalaciones",
            precio_min=70000,
            precio_max=150000,
            activo=1,
            prestador=self.prestador,
            categoria=categoria,
        )
        self.contratacion = Contratacion.objects.create(
            fecha=date.today(),
            fecha_solicitud=date.today(),
            estado="Completada",
            observacion='{"hora":"11:00","monto":"90000","direccion":"Calle 10 # 5-20","descripcion":"Servicio completado"}',
            prestador=self.prestador,
            servicio=servicio,
        )
        ClienteContratacion.objects.create(
            cliente=self.cliente,
            contratacion=self.contratacion,
        )

        session = self.client.session
        session["usuario_id"] = self.cliente.id_usuario
        session.save()

    def test_calificaciones_creates_and_updates_single_rating_per_cliente_and_contratacion(self):
        create_payload = {
            "idContratacion": self.contratacion.id_contratacion,
            "puntuacion": 4,
            "comentario": "Buen servicio",
        }
        create_response = self.client.post(
            "/calificaciones",
            data=json.dumps(create_payload),
            content_type="application/json",
        )

        self.assertEqual(create_response.status_code, 201)
        id_calificacion = create_response.json().get("idCalificacion")
        self.assertIsNotNone(id_calificacion)
        self.assertEqual(Calificacion.objects.count(), 1)

        calificacion = Calificacion.objects.get(id_calificacion=id_calificacion)
        self.assertEqual(calificacion.puntuacion, 4)
        self.assertEqual(calificacion.comentario, "Buen servicio")
        self.assertEqual(calificacion.prestador_id, self.prestador.id_prestador)
        self.assertTrue(
            ClienteCalificacion.objects.filter(
                cliente=self.cliente,
                calificacion=calificacion,
            ).exists()
        )

        update_payload = {
            "idContratacion": self.contratacion.id_contratacion,
            "puntuacion": 5,
            "comentario": "Excelente atencion",
        }
        update_response = self.client.post(
            "/calificaciones",
            data=json.dumps(update_payload),
            content_type="application/json",
        )

        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json().get("idCalificacion"), id_calificacion)
        self.assertEqual(Calificacion.objects.count(), 1)

        calificacion.refresh_from_db()
        self.assertEqual(calificacion.puntuacion, 5)
        self.assertEqual(calificacion.comentario, "Excelente atencion")
