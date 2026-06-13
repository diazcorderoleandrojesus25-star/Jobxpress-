from django.db import migrations
from django.utils import timezone


ROLES = [
    (1, "ROLE_ADMIN"),
    (2, "ROLE_CLIENTE"),
    (3, "ROLE_PRESTADOR"),
]

CATEGORIAS = [
    (1, "Plomeria"),
    (2, "Electricidad"),
    (3, "Carpinteria"),
    (4, "Limpieza General"),
    (5, "Soporte Tecnico"),
    (6, "Instalacion de Equipos"),
    (7, "Fisioterapia"),
    (8, "Salud"),
    (9, "Tutorias y Asesorias"),
    (10, "Cuidado de Mascotas"),
    (11, "Redaccion de Contenido"),
    (12, "Marketing Digital"),
]

SERVICIOS = [
    (1, "Plomeria residencial", "Atencion de fugas, reparaciones e instalaciones hidraulicas para hogar y negocio.", 50000.0, 180000.0, 1),
    (2, "Electricidad residencial", "Mantenimiento, revision e instalaciones electricas con enfoque preventivo.", 60000.0, 220000.0, 2),
    (3, "Carpinteria a medida", "Fabricacion, ajuste y reparacion de muebles, puertas y estructuras en madera.", 70000.0, 260000.0, 3),
    (4, "Limpieza general", "Jornadas de limpieza integral para viviendas, oficinas y espacios comerciales.", 45000.0, 160000.0, 4),
    (5, "Soporte tecnico", "Diagnostico y solucion de fallas en computadores, redes y equipos tecnologicos.", 50000.0, 200000.0, 5),
    (6, "Instalacion de equipos", "Montaje y puesta en funcionamiento de equipos domesticos o empresariales.", 55000.0, 210000.0, 6),
    (7, "Fisioterapia domiciliaria", "Sesiones de rehabilitacion y terapia fisica con atencion personalizada.", 80000.0, 180000.0, 7),
    (8, "Servicios de salud en casa", "Acompanamiento y asistencia basica orientada al bienestar del usuario.", 90000.0, 250000.0, 8),
    (9, "Tutorias y asesorias", "Apoyo academico y profesional para refuerzo de conocimientos y proyectos.", 40000.0, 150000.0, 9),
    (10, "Cuidado de mascotas", "Atencion, acompanamiento y cuidado responsable de animales de compania.", 35000.0, 140000.0, 10),
    (11, "Redaccion de contenido", "Creacion y edicion de textos para medios digitales, academicos o corporativos.", 50000.0, 170000.0, 11),
    (12, "Marketing digital", "Planeacion y ejecucion de acciones para presencia digital y captacion de clientes.", 90000.0, 300000.0, 12),
]

METODOS_PAGO = [
    (1, "Efectivo"),
    (2, "Transferencia Bancaria"),
    (3, "Tarjeta Debito"),
    (4, "Tarjeta Credito"),
    (5, "PSE"),
    (6, "Nequi"),
    (7, "Daviplata"),
]


def reset_sequence(apps, schema_editor, model_name):
    if schema_editor.connection.vendor != "postgresql":
        return

    model = apps.get_model("core", model_name)
    table = model._meta.db_table
    pk_column = model._meta.pk.column
    quoted_table = schema_editor.quote_name(table)
    quoted_pk = schema_editor.quote_name(pk_column)

    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            f"""
            SELECT setval(
                pg_get_serial_sequence(%s, %s),
                COALESCE(MAX({quoted_pk}), 1),
                MAX({quoted_pk}) IS NOT NULL
            )
            FROM {quoted_table}
            """,
            [table, pk_column],
        )


def seed_initial_data(apps, schema_editor):
    Rol = apps.get_model("core", "Rol")
    Categoria = apps.get_model("core", "Categoria")
    Servicio = apps.get_model("core", "Servicio")
    MetodoPago = apps.get_model("core", "MetodoPago")
    Usuario = apps.get_model("core", "Usuario")

    for pk, nombre in ROLES:
        Rol.objects.update_or_create(id_rol=pk, defaults={"rol": nombre})

    for pk, nombre in CATEGORIAS:
        Categoria.objects.update_or_create(
            id_categoria=pk,
            defaults={"nombre": nombre, "activo": 1},
        )

    for pk, nombre, descripcion, precio_min, precio_max, categoria_id in SERVICIOS:
        Servicio.objects.update_or_create(
            id_servicio=pk,
            defaults={
                "nombre": nombre,
                "descripcion": descripcion,
                "precio_min": precio_min,
                "precio_max": precio_max,
                "activo": 1,
                "prestador_id": None,
                "categoria_id": categoria_id,
            },
        )

    for pk, forma_pago in METODOS_PAGO:
        MetodoPago.objects.update_or_create(
            id_metodo_pago=pk,
            defaults={"forma_pago": forma_pago},
        )

    Usuario.objects.update_or_create(
        id_usuario=1,
        defaults={
            "nombre": "Administrador",
            "apellido": "Base",
            "email": "admin@jobxpress.local",
            "telefono": "3000000000",
            "contrasena": "$2b$12$rFF2hbjB7/V8J6XQUIjIdeOcG.zKHf7v5PxEV0G/7MB9GkzEqltYy",
            "direccion": "Calle 10 # 20-30",
            "created_at": timezone.now(),
            "updated_at": timezone.now(),
            "reset_token": None,
            "foto_perfil": None,
            "activo": 1,
            "rol_id": 1,
        },
    )

    for model_name in ("Rol", "Categoria", "Servicio", "MetodoPago", "Usuario"):
        reset_sequence(apps, schema_editor, model_name)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(seed_initial_data, migrations.RunPython.noop),
    ]
