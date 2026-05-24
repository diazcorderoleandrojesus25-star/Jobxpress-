from django.db import connection

from core.models import Rol, Usuario


def ensure_tables(*models) -> None:
    existing_tables = set(connection.introspection.table_names())
    models_to_create = []

    for model in models:
        if model._meta.db_table not in existing_tables:
            models_to_create.append(model)
            existing_tables.add(model._meta.db_table)

    if not models_to_create:
        return

    with connection.schema_editor() as schema_editor:
        for model in models_to_create:
            schema_editor.create_model(model)


def ensure_auth_tables() -> None:
    ensure_tables(Rol, Usuario)
