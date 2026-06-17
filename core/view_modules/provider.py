from .common import *


def _proximas_contrataciones_visibles(prestador, limite):
    if not prestador:
        return Contratacion.objects.none()

    hoy = timezone.localdate()
    return (
        Contratacion.objects.filter(prestador=prestador)
        .exclude(fecha=None)
        .exclude(Q(estado__icontains="rechaz") | Q(estado__icontains="cancel"))
        .filter(fecha__gte=hoy)
        .order_by("fecha")[:limite]
    )


def prestador_home(request):
    prestador = Prestador.objects.filter(usuario=request.usuario).first()
    servicios_qs = _get_or_create_prestador_services(prestador)
    servicios_activos = servicios_qs.count() if prestador else 0
    contrataciones = Contratacion.objects.filter(prestador=prestador) if prestador else Contratacion.objects.none()
    proximas = _proximas_contrataciones_visibles(prestador, 4)
    califs = Calificacion.objects.filter(prestador=prestador) if prestador else Calificacion.objects.none()
    promedio = califs.aggregate(avg=Avg("puntuacion")).get("avg") or 0
    ganancias = (
        Pago.objects.filter(contratacion__prestador=prestador).aggregate(total=Sum("monto")).get("total") or 0
        if prestador
        else 0
    )

    return render(
        request,
        "prestador/home.html",
        {
            "servicios_activos": servicios_activos,
            "promedio": round(promedio, 1) if promedio else 0,
            "ganancias": int(ganancias),
            "proximas": proximas,
        },
    )

def prestador_perfil(request):
    foto_url = _media_url(getattr(request.usuario, "foto_perfil", None))
    return render(
        request,
        "prestador/perfilprestador.html",
        {"usuario": request.usuario, "foto_url": foto_url},
    )

def prestador_perfil_actualizar(request):
    usuario = request.usuario
    telefono = _normalize_phone(request.POST.get("telefono", usuario.telefono))
    direccion = _normalize_address(request.POST.get("direccion", usuario.direccion))

    if not _is_valid_phone(telefono):
        return redirect("/prestador/perfil?error=telefono")
    if not _is_valid_address(direccion):
        return redirect("/prestador/perfil?error=direccion")

    usuario.nombre = request.POST.get("nombre", usuario.nombre).strip()
    usuario.apellido = request.POST.get("apellido", usuario.apellido).strip()
    usuario.email = request.POST.get("email", usuario.email).strip()
    usuario.telefono = telefono
    usuario.direccion = direccion
    foto = request.FILES.get("foto_perfil")
    eliminar_foto = request.POST.get("eliminar_foto") == "1"
    update_fields = ["nombre", "apellido", "email", "telefono", "direccion"]

    if eliminar_foto and usuario.foto_perfil:
        if default_storage.exists(usuario.foto_perfil):
            default_storage.delete(usuario.foto_perfil)
        usuario.foto_perfil = ""
        update_fields.append("foto_perfil")

    if foto:
        content_type = getattr(foto, "content_type", "") or ""
        if not content_type.startswith("image/"):
            return redirect("/prestador/perfil?error=foto")

        ext = os.path.splitext(foto.name or "")[1].lower() or ".jpg"
        filename = f"perfiles/prestador_{usuario.id_usuario}{ext}"

        if usuario.foto_perfil and default_storage.exists(usuario.foto_perfil):
            default_storage.delete(usuario.foto_perfil)

        saved_path = default_storage.save(filename, foto)
        usuario.foto_perfil = saved_path
        update_fields.append("foto_perfil")

    usuario.save(update_fields=update_fields)
    return redirect("/prestador/perfil?updated=1")

def prestador_dashboard(request):
    prestador = Prestador.objects.filter(usuario=request.usuario).first()
    servicios_qs = _get_or_create_prestador_services(prestador)
    servicios_activos = servicios_qs.count() if prestador else 0
    contrataciones = Contratacion.objects.filter(prestador=prestador) if prestador else Contratacion.objects.none()

    total = contrataciones.count()
    pendientes = contrataciones.filter(estado__icontains="pend").count()
    confirmadas = contrataciones.filter(estado__icontains="confirm").count()
    canceladas = contrataciones.filter(estado__icontains="rechaz").count()
    completadas = contrataciones.filter(estado__icontains="complet").count()

    ganancias = (
        Pago.objects.filter(contratacion__prestador=prestador).aggregate(total=Sum("monto")).get("total") or 0
        if prestador
        else 0
    )
    califs = Calificacion.objects.filter(prestador=prestador) if prestador else Calificacion.objects.none()
    promedio = califs.aggregate(avg=Avg("puntuacion")).get("avg") or 0

    # Distribucion de reseñas 1-5
    dist = {str(i): 0 for i in range(1, 6)}
    for row in califs.values("puntuacion").annotate(total=Count("id_calificacion")):
        dist[str(row["puntuacion"])] = row["total"]
    total_califs = califs.count()
    dist_pct = {
        str(i): (dist[str(i)] / total_califs * 100) if total_califs else 0 for i in range(1, 6)
    }

    # ultimas reseñas con cliente si existe
    ultimas = []
    for c in califs.order_by("-id_calificacion")[:4]:
        cliente_link = ClienteCalificacion.objects.filter(calificacion=c).select_related("cliente").first()
        cliente_name = (
            f"{cliente_link.cliente.nombre} {cliente_link.cliente.apellido}"
            if cliente_link and cliente_link.cliente
            else "Cliente"
        )
        ultimas.append({"cliente": cliente_name, "comentario": c.comentario, "puntuacion": c.puntuacion})

    # proximas citas
    proximas = _proximas_contrataciones_visibles(prestador, 5)

    return render(
        request,
        "prestador/dashboard.html",
        {
            "usuario": request.usuario,
            "servicios_activos": servicios_activos,
            "ganancias": int(ganancias),
            "promedio": round(promedio, 1) if promedio else 0,
            "total_contrataciones": total,
            "pendientes": pendientes,
            "confirmadas": confirmadas,
            "canceladas": canceladas,
            "completadas": completadas,
            "dist": dist,
            "dist_pct": dist_pct,
            "dist5": dist.get("5", 0),
            "dist4": dist.get("4", 0),
            "dist3": dist.get("3", 0),
            "dist2": dist.get("2", 0),
            "dist1": dist.get("1", 0),
            "dist5_pct": dist_pct.get("5", 0),
            "dist4_pct": dist_pct.get("4", 0),
            "dist3_pct": dist_pct.get("3", 0),
            "dist2_pct": dist_pct.get("2", 0),
            "dist1_pct": dist_pct.get("1", 0),
            "total_califs": total_califs,
            "ultimas": ultimas,
            "proximas": proximas,
        },
    )

def prestador_chat(request):
    return render(request, "prestador/chat.html")

def prestador_page(request, page):
    if page == "servicioprestador":
        prestador = Prestador.objects.filter(usuario=request.usuario).first()
        servicios = _get_or_create_prestador_services(prestador)
        servicio = servicios.first()
        promedio = (
            Calificacion.objects.filter(prestador=prestador).aggregate(avg=Avg("puntuacion")).get("avg") or 0
            if prestador
            else 0
        )
        return render(
            request,
            "prestador/servicioprestador.html",
            {
                "servicio": servicio,
                "servicios": servicios,
                "promedio": round(promedio, 1) if promedio else 0,
                "prestador": prestador,
            },
        )
    if page == "ganancias":
        prestador = Prestador.objects.filter(usuario=request.usuario).first()
        pagos = (
            Pago.objects.filter(contratacion__prestador=prestador)
            .select_related("contratacion__servicio")
            .order_by("-fecha")
            if prestador
            else Pago.objects.none()
        )
        total = pagos.aggregate(total=Sum("monto")).get("total") or 0
        count = pagos.count()
        promedio = int(total / count) if count else 0

        items = []
        for p in pagos[:20]:
            cliente_link = (
                ClienteContratacion.objects.filter(contratacion=p.contratacion)
                .select_related("cliente")
                .first()
            )
            cliente_name = (
                f"{cliente_link.cliente.nombre} {cliente_link.cliente.apellido}"
                if cliente_link and cliente_link.cliente
                else "Cliente"
            )
            items.append(
                {
                    "cliente": cliente_name,
                    "fecha": p.fecha.strftime("%Y-%m-%d") if p.fecha else "-",
                    "monto": p.monto,
                    "servicio": p.contratacion.servicio.nombre if p.contratacion and p.contratacion.servicio else "Servicio",
                    "inicial": (cliente_name[:1] or "C").upper(),
                }
            )

        return render(
            request,
            "prestador/ganancias.html",
            {
                "total": int(total),
                "count": count,
                "promedio": promedio,
                "pagos": items,
            },
        )
    if page == "valoraciones":
        prestador = Prestador.objects.filter(usuario=request.usuario).first()
        califs = (
            Calificacion.objects.filter(prestador=prestador).order_by("-id_calificacion")
            if prestador
            else Calificacion.objects.none()
        )
        total = califs.count()
        promedio = califs.aggregate(avg=Avg("puntuacion")).get("avg") or 0
        completados = (
            Contratacion.objects.filter(prestador=prestador, estado__icontains="complet").count()
            if prestador
            else 0
        )

        dist = {i: 0 for i in range(1, 6)}
        for row in califs.values("puntuacion").annotate(total=Count("id_calificacion")):
            dist[row["puntuacion"]] = row["total"]
        dist_pct = {i: (dist[i] / total * 100) if total else 0 for i in range(1, 6)}

        calif_items = []
        for c in califs[:10]:
            cliente_link = ClienteCalificacion.objects.filter(calificacion=c).select_related("cliente").first()
            cliente_name = (
                f"{cliente_link.cliente.nombre} {cliente_link.cliente.apellido}"
                if cliente_link and cliente_link.cliente
                else "Cliente"
            )
            calif_items.append(
                {
                    "cliente": cliente_name,
                    "puntuacion": c.puntuacion,
                    "comentario": c.comentario,
                    "fecha": getattr(c, "fecha_calificacion", None) or "-",
                }
            )

        return render(
            request,
            "prestador/valoraciones.html",
            {
                "promedio": round(promedio, 1) if promedio else 0,
                "total": total,
                "completados": completados,
                "dist": dist,
                "dist1": dist.get(1, 0),
                "dist2": dist.get(2, 0),
                "dist3": dist.get(3, 0),
                "dist4": dist.get(4, 0),
                "dist5": dist.get(5, 0),
                "dist1_pct": dist_pct.get(1, 0),
                "dist2_pct": dist_pct.get(2, 0),
                "dist3_pct": dist_pct.get(3, 0),
                "dist4_pct": dist_pct.get(4, 0),
                "dist5_pct": dist_pct.get(5, 0),
                "calificaciones": calif_items,
            },
        )

    return render(request, f"prestador/{page}.html")

def prestador_servicio_actualizar(request):
    prestador = Prestador.objects.filter(usuario=request.usuario).first()
    if not prestador:
        return _json_error("Prestador no encontrado", status=404)

    servicio_id = request.POST.get("servicio_id")
    descripcion = (request.POST.get("descripcion") or "").strip()
    precio_min = request.POST.get("precio_min")
    precio_max = request.POST.get("precio_max")

    servicio = None
    if servicio_id:
        servicio = Servicio.objects.filter(id_servicio=servicio_id, prestador=prestador).first()
    if servicio is None:
        servicio = _get_or_create_prestador_services(prestador).first()

    if servicio is None:
        return _json_error("Servicio no encontrado", status=404)

    if descripcion:
        prestador.descripcion = descripcion
    if precio_min:
        try:
            servicio.precio_min = float(precio_min)
        except ValueError:
            pass
    if precio_max:
        try:
            servicio.precio_max = float(precio_max)
        except ValueError:
            pass
    if servicio.prestador_id == prestador.id_prestador:
        servicio.save()
    if descripcion:
        prestador.save(update_fields=["descripcion"])

    return JsonResponse(
        {
            "ok": True,
            "descripcion": prestador.descripcion or servicio.descripcion,
            "precio_min": servicio.precio_min,
            "precio_max": servicio.precio_max,
        }
    )

def prestador_agenda_data(request):
    prestador = Prestador.objects.filter(usuario=request.usuario).first()
    if not prestador:
        return JsonResponse({"pendientes": [], "aceptadas": [], "eventos": []})

    contrataciones = Contratacion.objects.filter(prestador=prestador).select_related("servicio")

    pendientes = []
    aceptadas = []
    eventos = []
    for c in contrataciones:
        estado = (c.estado or "").lower()
        cliente_link = ClienteContratacion.objects.filter(contratacion=c).select_related("cliente").first()
        cliente_name = None
        if cliente_link and cliente_link.cliente:
            cliente_name = f"{cliente_link.cliente.nombre} {cliente_link.cliente.apellido}"

        obs = _parse_observacion(c.observacion)
        item = {
            "id": c.id_contratacion,
            "servicio": c.servicio.nombre if c.servicio else "Servicio",
            "cliente": cliente_name or "Cliente",
            "fecha": str(c.fecha) if c.fecha else "",
            "hora": obs.get("hora", ""),
            "direccion": obs.get("direccion", ""),
            "monto": obs.get("monto", ""),
            "descripcion": obs.get("descripcion", ""),
            "estado": c.estado or "",
        }

        if "pend" in estado:
            pendientes.append(item)
        elif "rechaz" in estado:
            continue
        else:
            aceptadas.append(item)

        if c.fecha:
            eventos.append({
                "title": item["servicio"],
                "start": str(c.fecha),
                "backgroundColor": "#4CAF50" if "confirm" in estado else "#29B6F6",
                "borderColor": "#4CAF50" if "confirm" in estado else "#29B6F6",
                "textColor": "white",
            })

    return JsonResponse({"pendientes": pendientes, "aceptadas": aceptadas, "eventos": eventos})

def prestador_agenda_aceptar(request, id):
    Contratacion.objects.filter(id_contratacion=id).update(estado="Confirmado")
    return JsonResponse({"ok": True})

def prestador_agenda_rechazar(request, id):
    Contratacion.objects.filter(id_contratacion=id).update(estado="Rechazado")
    return JsonResponse({"ok": True})
