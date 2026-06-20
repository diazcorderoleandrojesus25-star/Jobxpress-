from .common import *


def api_roles(request):
    if request.method == "GET":
        data = [{"idRol": r.id_rol, "rol": r.rol} for r in Rol.objects.all()]
        return JsonResponse(data, safe=False)

    payload = _parse_body(request)
    rol_name = payload.get("rol")
    if not rol_name:
        return _json_error("rol requerido")
    if Rol.objects.filter(rol__iexact=rol_name).exists():
        return _json_error("El rol ya existe", status=409)
    rol = Rol.objects.create(rol=rol_name)
    return JsonResponse({"idRol": rol.id_rol, "rol": rol.rol}, status=201)

def api_roles_detail(request, id):
    rol = Rol.objects.filter(id_rol=id).first()
    if not rol:
        return JsonResponse({}, status=404)

    if request.method == "GET":
        return JsonResponse({"idRol": rol.id_rol, "rol": rol.rol})

    if request.method == "PUT":
        payload = _parse_body(request)
        rol_name = payload.get("rol")
        if not rol_name:
            return _json_error("rol requerido")
        if Rol.objects.filter(rol__iexact=rol_name).exclude(id_rol=id).exists():
            return _json_error("Ya existe otro rol con ese nombre", status=409)
        rol.rol = rol_name
        rol.save(update_fields=["rol"])
        return JsonResponse({"idRol": rol.id_rol, "rol": rol.rol})

    rol.delete()
    return JsonResponse({}, status=204)

def api_categorias(request):
    if request.method == "GET":
        data = [{"idCategoria": c.id_categoria, "nombre": c.nombre} for c in Categoria.objects.all()]
        return JsonResponse(data, safe=False)

    payload = _parse_body(request)
    nombre = payload.get("nombre")
    if not nombre:
        return _json_error("nombre requerido")
    categoria = Categoria.objects.create(nombre=nombre, activo=1)
    return JsonResponse({"idCategoria": categoria.id_categoria, "nombre": categoria.nombre}, status=201)

def api_categorias_detail(request, id):
    categoria = Categoria.objects.filter(id_categoria=id).first()
    if not categoria:
        return JsonResponse({}, status=404)

    if request.method == "GET":
        return JsonResponse({"idCategoria": categoria.id_categoria, "nombre": categoria.nombre})

    if request.method == "PUT":
        payload = _parse_body(request)
        nombre = payload.get("nombre")
        if nombre:
            categoria.nombre = nombre
            categoria.save(update_fields=["nombre"])
        return JsonResponse({"idCategoria": categoria.id_categoria, "nombre": categoria.nombre})

    categoria.delete()
    return JsonResponse({}, status=204)

def api_servicios(request):
    if request.method == "GET":
        data = [
            {
                "idServicio": s.id_servicio,
                "nombre": s.nombre,
                "descripcion": s.descripcion,
                "precio_min": s.precio_min,
            "precio_max": s.precio_max,
                "categoria": {"idCategoria": s.categoria.id_categoria, "nombre": s.categoria.nombre}
                if s.categoria
                else None,
            }
            for s in Servicio.objects.select_related("categoria").all()
        ]
        return JsonResponse(data, safe=False)

    payload = _parse_body(request)
    categoria_id = payload.get("categoriaId") or (payload.get("categoria") or {}).get("idCategoria")
    categoria = Categoria.objects.filter(id_categoria=categoria_id).first()
    servicio = Servicio.objects.create(
        nombre=payload.get("nombre", ""),
        descripcion=payload.get("descripcion", ""),
        precio_min=payload.get("precio_min") or 0,
            precio_max=payload.get("precio_max") or 0,
        categoria=categoria,
    )
    return JsonResponse({"idServicio": servicio.id_servicio}, status=201)

def api_servicios_detail(request, id):
    servicio = Servicio.objects.filter(id_servicio=id).first()
    if not servicio:
        return JsonResponse({}, status=404)

    if request.method == "GET":
        return JsonResponse(
            {
                "idServicio": servicio.id_servicio,
                "nombre": servicio.nombre,
                "descripcion": servicio.descripcion,
                "precio_min": servicio.precio_min,
            "precio_max": servicio.precio_max,
            }
        )

    if request.method == "PUT":
        payload = _parse_body(request)
        servicio.nombre = payload.get("nombre", servicio.nombre)
        servicio.descripcion = payload.get("descripcion", servicio.descripcion)
        servicio.precio_min = payload.get("precio_min", servicio.precio_min)
        servicio.precio_max = payload.get("precio_max", servicio.precio_max)
        servicio.save()
        return JsonResponse({"idServicio": servicio.id_servicio})

    servicio.delete()
    return JsonResponse({}, status=204)

def api_metodos_pago(request):
    if request.method == "GET":
        data = [{"id": m.id_metodo_pago, "formaPago": m.forma_pago} for m in MetodoPago.objects.all()]
        return JsonResponse(data, safe=False)

    payload = _parse_body(request)
    metodo = MetodoPago.objects.create(forma_pago=payload.get("formaPago", ""))
    return JsonResponse({"id": metodo.id_metodo_pago, "formaPago": metodo.forma_pago}, status=201)

def api_metodos_pago_detail(request, id):
    metodo = MetodoPago.objects.filter(id_metodo_pago=id).first()
    if not metodo:
        return JsonResponse({}, status=404)

    if request.method == "GET":
        return JsonResponse({"id": metodo.id_metodo_pago, "formaPago": metodo.forma_pago})

    if request.method == "PUT":
        payload = _parse_body(request)
        metodo.forma_pago = payload.get("formaPago", metodo.forma_pago)
        metodo.save(update_fields=["forma_pago"])
        return JsonResponse({"id": metodo.id_metodo_pago, "formaPago": metodo.forma_pago})

    metodo.delete()
    return JsonResponse({}, status=204)

def api_pagos(request):
    if request.method == "GET":
        data = [
            {
                "idPago": p.id_pago,
                "monto": p.monto,
                "fecha": p.fecha.isoformat() if p.fecha else None,
            }
            for p in Pago.objects.all()
        ]
        return JsonResponse(data, safe=False)

    payload = _parse_body(request)
    pago = Pago.objects.create(
        monto=payload.get("monto") or 0,
        fecha=timezone.now(),
        contratacion_id=payload.get("idContratacion"),
        metodo_id=payload.get("idMetodo"),
    )
    return JsonResponse({"idPago": pago.id_pago}, status=201)

def api_pagos_detail(request, id):
    pago = Pago.objects.filter(id_pago=id).first()
    if not pago:
        return JsonResponse({}, status=404)

    if request.method == "GET":
        return JsonResponse(
            {
                "idPago": pago.id_pago,
                "monto": pago.monto,
                "fecha": pago.fecha.isoformat() if pago.fecha else None,
            }
        )

    if request.method == "PUT":
        payload = _parse_body(request)
        pago.monto = payload.get("monto", pago.monto)
        pago.save(update_fields=["monto"])
        return JsonResponse({"idPago": pago.id_pago})

    pago.delete()
    return JsonResponse({}, status=204)

def api_calificaciones(request):
    if request.method == "GET":
        data = [
            {
                "idCalificacion": c.id_calificacion,
                "puntuacion": c.puntuacion,
                "comentario": c.comentario,
            }
            for c in Calificacion.objects.all()
        ]
        return JsonResponse(data, safe=False)

    payload = _parse_body(request)
    puntuacion = payload.get("puntuacion") or 0
    comentario = payload.get("comentario", "")
    id_contratacion = payload.get("idContratacion")
    id_prestador = payload.get("idPrestador")
    cliente = getattr(request, "usuario", None)

    # Si el cliente ya calificó esta contratación, actualiza en lugar de duplicar
    if id_contratacion and cliente:
        existing_link = (
            ClienteCalificacion.objects.filter(
                cliente=cliente, calificacion__contratacion_id=id_contratacion
            )
            .select_related("calificacion")
            .first()
        )
        if existing_link and existing_link.calificacion:
            existing = existing_link.calificacion
            existing.puntuacion = puntuacion
            existing.comentario = comentario
            existing.save(update_fields=["puntuacion", "comentario"])
            return JsonResponse({"idCalificacion": existing.id_calificacion})

    if not id_prestador and id_contratacion:
        contratacion = Contratacion.objects.filter(id_contratacion=id_contratacion).first()
        if contratacion:
            id_prestador = contratacion.prestador_id

    calificacion = Calificacion.objects.create(
        puntuacion=puntuacion,
        comentario=comentario,
        contratacion_id=id_contratacion,
        prestador_id=id_prestador,
    )
    if cliente:
        ClienteCalificacion.objects.get_or_create(cliente=cliente, calificacion=calificacion)
    return JsonResponse({"idCalificacion": calificacion.id_calificacion}, status=201)

def api_calificaciones_detail(request, id):
    calificacion = Calificacion.objects.filter(id_calificacion=id).first()
    if not calificacion:
        return JsonResponse({}, status=404)

    if request.method == "GET":
        return JsonResponse(
            {
                "idCalificacion": calificacion.id_calificacion,
                "puntuacion": calificacion.puntuacion,
                "comentario": calificacion.comentario,
            }
        )

    if request.method == "PUT":
        payload = _parse_body(request)
        calificacion.puntuacion = payload.get("puntuacion", calificacion.puntuacion)
        calificacion.comentario = payload.get("comentario", calificacion.comentario)
        calificacion.save(update_fields=["puntuacion", "comentario"])
        return JsonResponse({"idCalificacion": calificacion.id_calificacion})

    calificacion.delete()
    return JsonResponse({}, status=204)

def api_contrataciones(request):
    if request.method == "GET":
        data = []
        for c in Contratacion.objects.all():
            cliente_link = ClienteContratacion.objects.filter(contratacion=c).first()
            data.append(
                {
                    "idContratacion": c.id_contratacion,
                    "fecha": c.fecha.isoformat() if c.fecha else None,
                    "estado": c.estado,
                    "idCliente": cliente_link.cliente_id if cliente_link else None,
                }
            )
        return JsonResponse(data, safe=False)

    payload = _parse_body(request)
    contratacion = Contratacion.objects.create(
        fecha=timezone.now().date(),
        estado=payload.get("estado", ""),
        prestador_id=payload.get("idPrestador"),
        servicio_id=payload.get("idServicio"),
    )
    id_cliente = payload.get("idCliente") or getattr(getattr(request, "usuario", None), "id_usuario", None)
    if id_cliente:
        ClienteContratacion.objects.create(cliente_id=id_cliente, contratacion=contratacion)

    return JsonResponse({"idContratacion": contratacion.id_contratacion}, status=201)

def api_contrataciones_detail(request, id):
    contratacion = Contratacion.objects.filter(id_contratacion=id).first()
    if not contratacion:
        return JsonResponse({}, status=404)

    if request.method == "GET":
        return JsonResponse(
            {
                "idContratacion": contratacion.id_contratacion,
                "fecha": contratacion.fecha.isoformat() if contratacion.fecha else None,
                "estado": contratacion.estado,
            }
        )

    if request.method == "PUT":
        payload = _parse_body(request)
        cliente = getattr(request, "usuario", None)
        if request.rol == "ROLE_CLIENTE" and not ClienteContratacion.objects.filter(
            cliente=cliente,
            contratacion=contratacion,
        ).exists():
            return _json_error("No puedes editar esta contratacion", status=403)

        obs = _parse_observacion(contratacion.observacion)

        fecha_nueva = payload.get("fecha", contratacion.fecha.isoformat() if contratacion.fecha else "")
        hora_actual = (obs.get("hora") or "").strip()
        hora_nueva = (payload.get("hora", hora_actual) or "").strip()
        monto_nuevo = payload.get("monto", obs.get("monto", ""))
        descripcion_nueva = payload.get("descripcion", obs.get("descripcion", ""))
        direccion_actual = obs.get("direccion", "")

        fecha_actual = contratacion.fecha.isoformat() if contratacion.fecha else ""
        fecha_cambio = (fecha_nueva or "") != fecha_actual
        hora_cambio = hora_nueva != hora_actual

        nuevo_estado = payload.get("estado", contratacion.estado)
        if fecha_cambio or hora_cambio:
            nuevo_estado = "Pendiente"

        if fecha_nueva:
            try:
                contratacion.fecha = datetime.strptime(fecha_nueva, "%Y-%m-%d").date()
            except ValueError:
                return _json_error("Fecha invalida", status=400)
        else:
            contratacion.fecha = None
        contratacion.estado = nuevo_estado
        contratacion.observacion = json.dumps(
            {
                "direccion": direccion_actual,
                "descripcion": descripcion_nueva,
                "hora": hora_nueva,
                "monto": monto_nuevo,
            },
            ensure_ascii=False,
        )
        contratacion.save(update_fields=["fecha", "estado", "observacion"])
        respuesta_prestador = _get_prestador_respuesta_estado(contratacion.estado)
        return JsonResponse(
            {
                "idContratacion": contratacion.id_contratacion,
                "fecha": contratacion.fecha.isoformat() if contratacion.fecha else "",
                "hora": hora_nueva,
                "monto": monto_nuevo,
                "descripcion": descripcion_nueva,
                "estado": contratacion.estado,
                "respuestaPrestador": respuesta_prestador,
                "prestadorAcepto": respuesta_prestador == "aceptado",
                "prestadorRespondio": respuesta_prestador not in ("pendiente", ""),
                "reenviada": fecha_cambio or hora_cambio,
            }
        )

    contratacion.delete()
    return JsonResponse({}, status=204)
