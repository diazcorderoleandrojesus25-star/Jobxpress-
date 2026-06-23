from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from core.models import Prestador, PrestadorCategoria, Rol, Servicio, Usuario


PASSWORD_HASH = "$2b$12$rFF2hbjB7/V8J6XQUIjIdeOcG.zKHf7v5PxEV0G/7MB9GkzEqltYy"

BASE_SERVICES = [
    (1, "Plomeria residencial", "Plomeria", 50000.0, 180000.0),
    (2, "Electricidad residencial", "Electricidad", 60000.0, 220000.0),
    (3, "Carpinteria a medida", "Carpinteria", 70000.0, 260000.0),
    (4, "Limpieza general", "Limpieza", 45000.0, 160000.0),
    (5, "Soporte tecnico", "Soporte tecnico", 50000.0, 200000.0),
    (6, "Instalacion de equipos", "Instalacion", 55000.0, 210000.0),
    (7, "Fisioterapia domiciliaria", "Fisioterapia", 80000.0, 180000.0),
    (8, "Servicios de salud en casa", "Salud", 90000.0, 250000.0),
    (9, "Tutorias y asesorias", "Tutorias y asesorias", 40000.0, 150000.0),
    (10, "Cuidado de mascotas", "Cuidado de mascotas", 35000.0, 140000.0),
    (11, "Redaccion de contenido", "Redaccion", 50000.0, 170000.0),
    (12, "Marketing digital", "Marketing digital", 90000.0, 300000.0),
]

EXTRA_PROVIDERS_BY_SERVICE = {
    1: [("Bruno", "Alfaro"), ("Sergio", "Castaneda"), ("Emiliano", "Paredes")],
    2: [("Hector", "Lizarazo"), ("Adrian", "Montero"), ("Mauricio", "Salgado")],
    3: [("Rafael", "Rendon"), ("Javier", "Escobar"), ("Gustavo", "Pimentel")],
    4: [("Fabian", "Mora"), ("Pablo", "Navarrete"), ("Cristian", "Fajardo")],
    5: [("Alberto", "Velandia"), ("Rodrigo", "Ocampo"), ("Lorenzo", "Camargo")],
    6: [("Samuel", "Tellez"), ("Hernan", "Duque"), ("Ulises", "Cabrera")],
    7: [("Ramon", "Ariza"), ("Eugenio", "Galvis"), ("Agustin", "Velez")],
    8: [("Cesar", "Quintana"), ("Mateo", "Berrio"), ("Ivan", "Roldan")],
    9: [("Nestor", "Arroyave"), ("Diego", "Sepulveda"), ("Leonardo", "Fonseca")],
    10: [("Andres", "Caicedo"), ("Sebastian", "Graterol"), ("Camilo", "Montalvo")],
    11: [("Valentin", "Villamarin"), ("Felipe", "Pedraza"), ("Oscar", "Benavides")],
    12: [("Julian", "Jaramillo"), ("David", "Saravia"), ("Ricardo", "Restrepo")],
}

DAYS = ["Lun a Vie", "Lun a Sab", "Mar a Dom"]
HOURS = ["8:00am - 5:00pm", "9:00am - 6:00pm", "7:00am - 3:00pm"]


class Command(BaseCommand):
    help = "Agrega 3 prestadores demo adicionales por servicio sin borrar ni reemplazar usuarios existentes."

    def handle(self, *args, **options):
        now = timezone.now()
        created_users = 0
        created_prestadores = 0

        with transaction.atomic():
            rol_prestador, _ = Rol.objects.get_or_create(
                rol="ROLE_PRESTADOR",
                defaults={"id_rol": 3},
            )

            for service_id, _service_name, service_label, _precio_min, _precio_max in BASE_SERVICES:
                base_service = (
                    Servicio.objects.filter(id_servicio=service_id)
                    .select_related("categoria")
                    .first()
                )
                if not base_service or not base_service.categoria_id:
                    continue

                for index, (first_name, last_name) in enumerate(EXTRA_PROVIDERS_BY_SERVICE[service_id], start=1):
                    email = f"extra-prestador-{service_id:02d}-{index}@jobxpress.local"

                    usuario, user_created = Usuario.objects.get_or_create(
                        email=email,
                        defaults={
                            "nombre": first_name,
                            "apellido": last_name,
                            "telefono": f"31{service_id:02d}{index:02d}7788{index}",
                            "contrasena": PASSWORD_HASH,
                            "direccion": f"Calle Extra {service_id + 20} # {index * 5}-{service_id}",
                            "created_at": now,
                            "updated_at": now,
                            "reset_token": None,
                            "foto_perfil": None,
                            "activo": 1,
                            "rol_id": rol_prestador.id_rol,
                        },
                    )
                    if user_created:
                        created_users += 1
                    else:
                        Usuario.objects.filter(pk=usuario.pk).update(
                            nombre=first_name,
                            apellido=last_name,
                            telefono=f"31{service_id:02d}{index:02d}7788{index}",
                            contrasena=PASSWORD_HASH,
                            direccion=f"Calle Extra {service_id + 20} # {index * 5}-{service_id}",
                            updated_at=now,
                            activo=1,
                            rol_id=rol_prestador.id_rol,
                        )

                    prestador, prestador_created = Prestador.objects.get_or_create(
                        usuario=usuario,
                        defaults={
                            "descripcion": (
                                f"Prestador adicional especializado en {service_label.lower()} "
                                "con atencion puntual y servicio a domicilio."
                            ),
                            "dias_atencion": DAYS[index - 1],
                            "horario_atencion": HOURS[index - 1],
                        },
                    )
                    if prestador_created:
                        created_prestadores += 1

                    Prestador.objects.filter(pk=prestador.pk).update(
                        descripcion=(
                            f"Prestador adicional especializado en {service_label.lower()} "
                            "con atencion puntual y servicio a domicilio."
                        ),
                        dias_atencion=DAYS[index - 1],
                        horario_atencion=HOURS[index - 1],
                    )

                    PrestadorCategoria.objects.get_or_create(
                        prestador=prestador,
                        categoria_id=base_service.categoria_id,
                    )

        self.stdout.write(
            self.style.SUCCESS(
                "Prestadores demo adicionales sincronizados sin borrar usuarios existentes: "
                f"+{created_users} usuarios, "
                f"+{created_prestadores} prestadores."
            )
        )
