from django.db import migrations


BASE_SERVICE_IDS = list(range(1, 13))


def _normalize_key(value):
    return (value or "").strip().casefold()


def normalize_catalog_services(apps, schema_editor):
    Servicio = apps.get_model("core", "Servicio")
    Contratacion = apps.get_model("core", "Contratacion")

    base_services = list(Servicio.objects.filter(id_servicio__in=BASE_SERVICE_IDS))
    base_by_key = {
        (_normalize_key(service.nombre), service.categoria_id): service for service in base_services
    }
    base_by_category = {}
    for service in base_services:
        base_by_category.setdefault(service.categoria_id, []).append(service)

    Servicio.objects.filter(id_servicio__in=BASE_SERVICE_IDS).update(prestador_id=None, activo=1)

    extra_services = list(Servicio.objects.exclude(id_servicio__in=BASE_SERVICE_IDS))
    for extra in extra_services:
        target = base_by_key.get((_normalize_key(extra.nombre), extra.categoria_id))
        if target is None:
            candidates = base_by_category.get(extra.categoria_id, [])
            if len(candidates) == 1:
                target = candidates[0]

        if target is not None and target.id_servicio != extra.id_servicio:
            Contratacion.objects.filter(servicio_id=extra.id_servicio).update(
                servicio_id=target.id_servicio
            )

        if not Contratacion.objects.filter(servicio_id=extra.id_servicio).exists():
            extra.delete()


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0007_backfill_prestador_servicios"),
    ]

    operations = [
        migrations.RunPython(normalize_catalog_services, migrations.RunPython.noop),
    ]
