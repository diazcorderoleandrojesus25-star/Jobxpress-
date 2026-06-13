from django.db import migrations


BASE_SERVICE_IDS = list(range(1, 13))


def cleanup_extra_services(apps, schema_editor):
    Servicio = apps.get_model("core", "Servicio")
    Servicio.objects.exclude(id_servicio__in=BASE_SERVICE_IDS).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0005_cleanup_non_admin_users"),
    ]

    operations = [
        migrations.RunPython(cleanup_extra_services, migrations.RunPython.noop),
    ]
