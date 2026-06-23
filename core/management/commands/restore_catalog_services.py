from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Contratacion, Servicio


BASE_SERVICE_IDS = list(range(1, 13))


def _normalize_key(value: str | None) -> str:
    return (value or "").strip().casefold()


class Command(BaseCommand):
    help = "Deja solo los 12 servicios base compartidos y elimina los duplicados de prueba."

    def handle(self, *args, **options):
        moved_contracts = 0
        removed_services = 0

        with transaction.atomic():
            base_services = list(
                Servicio.objects.filter(id_servicio__in=BASE_SERVICE_IDS).select_related("categoria")
            )
            base_by_key = {
                (_normalize_key(service.nombre), service.categoria_id): service for service in base_services
            }
            base_by_category = {}
            for service in base_services:
                base_by_category.setdefault(service.categoria_id, []).append(service)

            # El catalogo visible en registro debe usar las 12 filas base.
            Servicio.objects.filter(id_servicio__in=BASE_SERVICE_IDS).update(prestador=None, activo=1)

            extra_services = list(
                Servicio.objects.exclude(id_servicio__in=BASE_SERVICE_IDS).select_related("categoria")
            )
            for extra in extra_services:
                target = base_by_key.get((_normalize_key(extra.nombre), extra.categoria_id))
                if target is None:
                    candidates = base_by_category.get(extra.categoria_id, [])
                    if len(candidates) == 1:
                        target = candidates[0]

                if target is not None and target.id_servicio != extra.id_servicio:
                    moved = Contratacion.objects.filter(servicio_id=extra.id_servicio).update(
                        servicio_id=target.id_servicio
                    )
                    moved_contracts += moved

                if not Contratacion.objects.filter(servicio_id=extra.id_servicio).exists():
                    extra.delete()
                    removed_services += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Catalogo normalizado: se movieron {moved_contracts} contrataciones y se eliminaron {removed_services} servicios duplicados."
            )
        )
