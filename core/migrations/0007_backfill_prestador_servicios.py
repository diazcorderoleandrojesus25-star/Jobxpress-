from django.db import migrations


def backfill_prestador_servicios(apps, schema_editor):
    Prestador = apps.get_model("core", "Prestador")
    PrestadorCategoria = apps.get_model("core", "PrestadorCategoria")
    Servicio = apps.get_model("core", "Servicio")

    prestador_ids = list(Prestador.objects.values_list("id_prestador", flat=True))
    if not prestador_ids:
        return

    prestadores_con_servicio = set(
        Servicio.objects.filter(prestador__isnull=False).values_list("prestador_id", flat=True)
    )

    categorias_por_prestador = {}
    for prestador_id, categoria_id in PrestadorCategoria.objects.filter(
        prestador_id__in=prestador_ids
    ).values_list("prestador_id", "categoria_id"):
        categorias_por_prestador.setdefault(prestador_id, []).append(categoria_id)

    servicio_por_categoria = {}
    for categoria_id, servicio_id in Servicio.objects.filter(prestador__isnull=True).order_by(
        "categoria_id", "id_servicio"
    ).values_list("categoria_id", "id_servicio"):
        servicio_por_categoria.setdefault(categoria_id, servicio_id)

    for prestador_id in prestador_ids:
        if prestador_id in prestadores_con_servicio:
            continue

        categoria_ids = categorias_por_prestador.get(prestador_id, [])
        if len(categoria_ids) != 1:
            continue

        servicio_id = servicio_por_categoria.get(categoria_ids[0])
        if not servicio_id:
            continue

        Servicio.objects.filter(
            id_servicio=servicio_id,
            prestador__isnull=True,
        ).update(prestador_id=prestador_id)


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0006_cleanup_extra_services"),
    ]

    operations = [
        migrations.RunPython(backfill_prestador_servicios, migrations.RunPython.noop),
    ]
