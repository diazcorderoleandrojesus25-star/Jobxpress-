# Fixtures iniciales de Jobxpress

Este directorio contiene los datos minimos de arranque para una instalacion "punto 0" del proyecto.

## Archivos incluidos

- `roles.json`: roles base requeridos por la logica de autenticacion y redireccion.
- `categorias.json`: categorias maestras alineadas con las vistas publicas y filtros del cliente.
- `servicios_base.json`: servicios plantilla necesarios para el home del cliente y el registro de prestadores.
- `metodos_pago.json`: formas de pago habilitadas para registrar pagos.
- `usuarios_base.json`: usuario administrador inicial para acceso tecnico o funcional.
- `configuracion_inicial.json`: placeholder vacio. En la version actual no existe un modelo de parametrizacion persistente.

## Orden de carga recomendado

```powershell
python manage.py loaddata core/fixtures/roles.json
python manage.py loaddata core/fixtures/categorias.json
python manage.py loaddata core/fixtures/servicios_base.json
python manage.py loaddata core/fixtures/metodos_pago.json
python manage.py loaddata core/fixtures/usuarios_base.json
python manage.py loaddata core/fixtures/configuracion_inicial.json
```

## Usuario base opcional

- Correo: `admin@jobxpress.local`
- Contrasena: `Admin123*`

Se recomienda cambiar esta contrasena inmediatamente despues de la primera instalacion.

## Notas tecnicas

- Las fixtures usan los modelos reales definidos en `core.models`.
- Los roles conservan los IDs esperados por `templates/registro.html` y por la redireccion de `core/view_modules/auth.py`.
- Las categorias fueron definidas segun las rutas y paginas publicas ya implementadas en el modulo cliente.
- Los servicios base son necesarios porque el registro de prestadores exige seleccionar un servicio activo existente.
