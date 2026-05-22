# 4.1 Componente de Carga de Datos Origen - Jobxpress

Para el proyecto **Jobxpress**, el componente de carga de datos origen se implementa mediante **Django Fixtures** en formato JSON, ubicadas en la ruta `core/fixtures/`. Su objetivo es asegurar que cada nueva instalacion del sistema pueda iniciar con un conjunto minimo de datos maestros, de forma **controlada, repetible y consistente**, sin depender exclusivamente de registros manuales desde la interfaz administrativa.

En el estado actual del proyecto, los modelos que funcionan como catalogos base son:

- `Rol`
- `Categoria`
- `Servicio`
- `MetodoPago`
- `Usuario` (solo para usuario administrador base opcional)

Con base en estos modelos, se definio la siguiente estructura de carga inicial:

| Archivo de origen | Tipo | Contenido esperado | Finalidad |
| --- | --- | --- | --- |
| `core/fixtures/roles.json` | Fixture Django | Roles del sistema (`ROLE_ADMIN`, `ROLE_CLIENTE`, `ROLE_PRESTADOR`) | Garantizar perfiles minimos requeridos por autenticacion, registro y redireccion |
| `core/fixtures/categorias.json` | Fixture Django | Categorias maestras de servicios | Permitir la clasificacion inicial de servicios y activar las vistas publicas por categoria |
| `core/fixtures/servicios_base.json` | Fixture Django | Servicios plantilla asociados a las categorias iniciales | Permitir el registro inicial de prestadores y poblar la oferta minima visible del aplicativo |
| `core/fixtures/metodos_pago.json` | Fixture Django | Metodos de pago habilitados | Soportar el registro inicial de pagos dentro del sistema |
| `core/fixtures/usuarios_base.json` | Fixture Django | Usuario administrador base | Facilitar la puesta en marcha funcional y pruebas iniciales del aplicativo |
| `core/fixtures/configuracion_inicial.json` | Fixture Django | Placeholder vacio | Reservar la estructura para futura parametrizacion, ya que hoy no existe un modelo de configuracion persistente |

## Ajuste al proyecto real

En Jobxpress no existe actualmente un modelo especifico de configuracion general, por lo que **no corresponde inventar datos de parametrizacion que aun no tienen soporte en base de datos**. Por esta razon, el archivo `configuracion_inicial.json` se conserva como placeholder tecnico y la carga efectiva se concentra en los catalogos realmente implementados.

Del mismo modo, las fixtures creadas respetan decisiones ya presentes en el codigo fuente:

- El proceso de registro publico usa los IDs de rol `2` y `3` para cliente y prestador.
- La logica de navegacion interna reconoce los roles `ROLE_ADMIN`, `ROLE_CLIENTE` y `ROLE_PRESTADOR`.
- Las categorias iniciales se definieron conforme a las rutas, plantillas y filtros ya disponibles en el modulo cliente, como `plomeria`, `electricidad`, `carpinteria`, `limpiezageneral`, `soportetecnico`, `instalacion`, `fisioterapia`, `salud`, `asesorias`, `cuidadores`, `redaccion` y `marketing`.
- Adicionalmente, se incluyeron servicios base porque el flujo de registro de prestadores exige seleccionar un servicio existente; sin esta carga, una instalacion vacia permitiria registrar clientes, pero no prestadores.

## Procedimiento de carga

Las fixtures se cargan mediante el mecanismo estandar de Django:

```powershell
python manage.py loaddata core/fixtures/roles.json
python manage.py loaddata core/fixtures/categorias.json
python manage.py loaddata core/fixtures/servicios_base.json
python manage.py loaddata core/fixtures/metodos_pago.json
python manage.py loaddata core/fixtures/usuarios_base.json
python manage.py loaddata core/fixtures/configuracion_inicial.json
```

## Justificacion tecnica

La incorporacion de este componente evita que la instalacion inicial dependa exclusivamente de operaciones manuales. En consecuencia, mejora:

- la repetibilidad de despliegues en nuevos entornos
- la consistencia de catalogos maestros
- la preparacion de ambientes de prueba
- la continuidad operativa del sistema
- la estandarizacion del arranque funcional de Jobxpress

En conclusion, para Jobxpress el componente de carga de datos origen queda formalmente soportado por fixtures JSON alineadas con los modelos reales del aplicativo, cubriendo especialmente los catalogos criticos de **categorias de servicios** y **metodos de pago**, ademas de los **roles**, los **servicios base necesarios para el flujo de prestadores** y un **usuario administrador base opcional** para la puesta en marcha.
