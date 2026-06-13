from django.db import migrations


ADMIN_EMAIL = "admin@jobxpress.local"


def cleanup_non_admin_users(apps, schema_editor):
    Usuario = apps.get_model("core", "Usuario")
    Usuario.objects.exclude(email=ADMIN_EMAIL).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0004_update_demo_provider_names"),
    ]

    operations = [
        migrations.RunPython(cleanup_non_admin_users, migrations.RunPython.noop),
    ]
