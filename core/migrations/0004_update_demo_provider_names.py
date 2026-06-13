from django.db import migrations
from django.utils import timezone


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


def update_demo_provider_names(apps, schema_editor):
    Usuario = apps.get_model("core", "Usuario")
    now = timezone.now()

    for service_id, providers in PROVIDERS_BY_SERVICE.items():
        for index, (first_name, last_name) in enumerate(providers, start=1):
            email = f"prestador{service_id:02d}{index}@jobxpress.local"
            Usuario.objects.filter(email=email).update(
                nombre=first_name,
                apellido=last_name,
                updated_at=now,
            )


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0003_seed_demo_providers"),
    ]

    operations = [
        migrations.RunPython(update_demo_provider_names, migrations.RunPython.noop),
    ]
