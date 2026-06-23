from __future__ import annotations

import re

from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import Servicio, Usuario


DEMO_EMAIL_PATTERNS = (
    re.compile(r"^extra-prestador-\d{2}-\d@jobxpress\.local$"),
    re.compile(r"^prestador\d{4}@jobxpress\.local$"),
)


def _is_demo_email(email: str) -> bool:
    email = (email or "").strip()
    return any(pattern.fullmatch(email) for pattern in DEMO_EMAIL_PATTERNS)


class Command(BaseCommand):
    help = "Elimina usuarios demo prestadores y sus servicios de prueba, sin tocar el admin."

    def handle(self, *args, **options):
        with transaction.atomic():
            demo_users = Usuario.objects.filter(email__endswith="@jobxpress.local").filter(
                rol__rol="ROLE_PRESTADOR"
            )
            demo_users = [user for user in demo_users if _is_demo_email(user.email)]
            demo_user_ids = [user.id_usuario for user in demo_users]

            if not demo_user_ids:
                self.stdout.write(self.style.SUCCESS("No se encontraron usuarios demo para eliminar."))
                return

            services_qs = Servicio.objects.filter(prestador__usuario_id__in=demo_user_ids)
            services_count = services_qs.count()
            services_qs.delete()

            users_qs = Usuario.objects.filter(id_usuario__in=demo_user_ids)
            users_count = users_qs.count()
            users_qs.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Se eliminaron {users_count} usuarios demo y {services_count} servicios de prueba."
            )
        )
