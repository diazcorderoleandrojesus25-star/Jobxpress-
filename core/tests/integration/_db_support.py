from django.db import connection

from core.models import Rol, Usuario


def ensure_auth_tables() -> None:
    existing_tables = set(connection.introspection.table_names())
    models_to_create = []

    if Rol._meta.db_table not in existing_tables:
        models_to_create.append(Rol)
        existing_tables.add(Rol._meta.db_table)

    if Usuario._meta.db_table not in existing_tables:
        models_to_create.append(Usuario)

    if not models_to_create:
        return

    with connection.schema_editor() as schema_editor:
        for model in models_to_create:
            schema_editor.create_model(model)
