from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Servicio


class Command(BaseCommand):
    help = "Elimina los servicios demo extra creados por error, sin tocar usuarios ni prestadores."

    def handle(self, *args, **options):
        with transaction.atomic():
            qs = Servicio.objects.filter(prestador__usuario__email__startswith="extra-prestador-")
            count = qs.count()
            qs.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Se eliminaron {count} servicios demo extra sin tocar usuarios ni prestadores."
            )
        )

