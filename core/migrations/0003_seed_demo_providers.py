from django.db import migrations
from django.utils import timezone


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

PROVIDERS_BY_SERVICE = {
    1: [("Luis", "Herrera"), ("Marta", "Benitez"), ("Diego", "Salazar")],
    2: [("Oscar", "Rivas"), ("Natalia", "Pardo"), ("Julian", "Cortes")],
    3: [("Felipe", "Quintero"), ("Laura", "Mejia"), ("Ruben", "Galindo")],
    4: [("Ana", "Cardenas"), ("Paola", "Duarte"), ("Erika", "Molina")],
    5: [("Kevin", "Vargas"), ("Diana", "Lozano"), ("Miguel", "Ortega")],
    6: [("Carlos", "Prieto"), ("Valentina", "Cruz"), ("Sebastian", "Leon")],
    7: [("Andrea", "Fuentes"), ("Mariana", "Castro"), ("Ricardo", "Becerra")],
    8: [("Claudia", "Navarro"), ("Jorge", "Pineda"), ("Lucia", "Romero")],
    9: [("Nicolas", "Arias"), ("Sofia", "Calderon"), ("Tomas", "Cifuentes")],
    10: [("Paula", "Rojas"), ("Andres", "Beltran"), ("Catalina", "Ospina")],
    11: [("Gabriela", "Montes"), ("Daniel", "Acosta"), ("Elena", "Villalba")],
    12: [("Camilo", "Nieto"), ("Manuela", "Reyes"), ("Esteban", "Vera")],
}

DAYS = ["Lun a Vie", "Lun a Sab", "Mar a Dom"]
HOURS = ["8:00am - 5:00pm", "9:00am - 6:00pm", "7:00am - 3:00pm"]


def seed_demo_providers(apps, schema_editor):
    Rol = apps.get_model("core", "Rol")
    Usuario = apps.get_model("core", "Usuario")
    Prestador = apps.get_model("core", "Prestador")
    PrestadorCategoria = apps.get_model("core", "PrestadorCategoria")
    Servicio = apps.get_model("core", "Servicio")

    rol_prestador, _ = Rol.objects.get_or_create(
        rol="ROLE_PRESTADOR",
        defaults={"id_rol": 3},
    )
    now = timezone.now()

    for service_id, service_name, service_label, precio_min, precio_max in BASE_SERVICES:
        base_service = Servicio.objects.filter(id_servicio=service_id).select_related("categoria").first()
        if not base_service or not base_service.categoria_id:
            continue

        for index, (first_name, last_name) in enumerate(PROVIDERS_BY_SERVICE[service_id], start=1):
            email = f"prestador{service_id:02d}{index}@jobxpress.local"
            usuario, _ = Usuario.objects.update_or_create(
                email=email,
                defaults={
                    "nombre": first_name,
                    "apellido": last_name,
                    "telefono": f"300{service_id:02d}{index:02d}45{index:02d}",
                    "contrasena": PASSWORD_HASH,
                    "direccion": f"Calle {service_id + 10} # {index * 7}-{service_id}",
                    "created_at": now,
                    "updated_at": now,
                    "reset_token": None,
                    "foto_perfil": None,
                    "activo": 1,
                    "rol_id": rol_prestador.id_rol,
                },
            )

            prestador, _ = Prestador.objects.update_or_create(
                usuario=usuario,
                defaults={
                    "descripcion": (
                        f"Prestador especializado en {service_label.lower()} "
                        "con atencion puntual y servicio a domicilio."
                    ),
                    "dias_atencion": DAYS[index - 1],
                    "horario_atencion": HOURS[index - 1],
                },
            )

            PrestadorCategoria.objects.get_or_create(
                prestador=prestador,
                categoria_id=base_service.categoria_id,
            )

            Servicio.objects.update_or_create(
                nombre=service_name,
                prestador=prestador,
                defaults={
                    "descripcion": base_service.descripcion,
                    "precio_min": precio_min,
                    "precio_max": precio_max,
                    "activo": 1,
                    "categoria_id": base_service.categoria_id,
                },
            )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0002_seed_initial_data"),
    ]

    operations = [
        migrations.RunPython(seed_demo_providers, migrations.RunPython.noop),
    ]
