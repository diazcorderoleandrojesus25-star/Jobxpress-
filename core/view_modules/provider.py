from .common import *


def _proximas_contrataciones_visibles(prestador, limite):
    if not prestador:
        return Contratacion.objects.none()

    visibles = []
    now = timezone.now()
    contrataciones = (
        Contratacion.objects.filter(prestador=prestador)
        .exclude(fecha=None)
        .exclude(Q(estado__icontains="rechaz") | Q(estado__icontains="cancel"))
        .order_by("fecha", "id_contratacion")
    )
    for contratacion in contrataciones:
        if _contratacion_esta_expirada(contratacion, now=now):
            continue
        visibles.append(contratacion)
        if len(visibles) >= limite:
            break
    return visibles


def _cliente_nombre_desde_link(link):
    if not link or not link.cliente:
        return ""

    nombre = f"{(link.cliente.nombre or '').strip()} {(link.cliente.apellido or '').strip()}".strip()
    return nombre or (link.cliente.email or "").strip()


def _cliente_nombre_desde_observacion(contratacion):
    obs = _parse_observacion(getattr(contratacion, "observacion", None))
    return (obs.get("cliente_nombre") or obs.get("cliente") or "").strip()


def _cliente_nombre_map(contrataciones):
    nombres = {}
    if not contrataciones:
        return nombres

    for link in ClienteContratacion.objects.filter(contratacion__in=contrataciones).select_related("cliente"):
        nombre = _cliente_nombre_desde_link(link)
        if nombre:
            nombres[link.contratacion_id] = nombre

    return nombres


def _monto_desde_observacion(contratacion):
    obs = _parse_observacion(getattr(contratacion, "observacion", None))
    try:
        return float(obs.get("monto") or 0)
    except (TypeError, ValueError):
        return 0.0


def _contratacion_programada_datetime(contratacion):
    fecha = getattr(contratacion, "fecha", None)
    if not fecha:
        return None

    obs = _parse_observacion(getattr(contratacion, "observacion", None))
    hora_raw = (obs.get("hora") or "").strip()
    if hora_raw:
        for fmt in ("%H:%M", "%H:%M:%S"):
            try:
                hora = datetime.strptime(hora_raw, fmt).time()
                return datetime.combine(fecha, hora)
            except ValueError:
                continue

    return datetime.combine(fecha, datetime.max.time().replace(microsecond=0))


def _contratacion_esta_expirada(contratacion, now=None):
    programada = _contratacion_programada_datetime(contratacion)
    if programada is None:
        return False

    now = now or timezone.now()
    if timezone.is_aware(now) and timezone.is_naive(programada):
        programada = timezone.make_aware(programada, now.tzinfo)
    return now >= programada


def _ganancias_prestador_data(prestador, limite=20):
    if not prestador:
        return 0.0, 0, []

    contrataciones_qs = (
        Contratacion.objects.filter(prestador=prestador)
        .select_related("servicio")
        .order_by("-fecha_solicitud", "-id_contratacion")
    )
    cliente_map = _cliente_nombre_map(contrataciones_qs)

    items = []
    total = 0.0
    count = 0
    procesadas = set()

    pagos_qs = (
        Pago.objects.filter(contratacion__prestador=prestador)
        .select_related("contratacion__servicio")
        .order_by("-fecha", "-id_pago")
    )
    for pago in pagos_qs:
        contratacion = pago.contratacion
        cliente_name = cliente_map.get(contratacion.id_contratacion) if contratacion else ""
        if not cliente_name and contratacion:
            cliente_name = _cliente_nombre_desde_observacion(contratacion)
        if not cliente_name:
            cliente_name = "Cliente"

        monto = float(pago.monto or 0)
        if monto <= 0 and contratacion:
            monto = _monto_desde_observacion(contratacion)

        fecha_item = pago.fecha.strftime("%Y-%m-%d") if pago.fecha else "-"
        if contratacion and contratacion.fecha_solicitud:
            fecha_item = contratacion.fecha_solicitud.strftime("%Y-%m-%d")

        items.append(
            {
                "cliente": cliente_name,
                "fecha": fecha_item,
                "monto": monto,
                "servicio": (
                    contratacion.servicio.nombre
                    if contratacion and contratacion.servicio
                    else "Servicio"
                ),
                "inicial": (cliente_name[:1] or "C").upper(),
                "_sort": pago.fecha or contratacion.fecha_solicitud if contratacion else None,
            }
        )
        total += monto
        count += 1
        if contratacion:
            procesadas.add(contratacion.id_contratacion)

    for contratacion in contrataciones_qs:
        if contratacion.id_contratacion in procesadas:
            continue

        estado_low = (contratacion.estado or "").lower()
        if "confirm" not in estado_low and "complet" not in estado_low:
            continue

        monto = _monto_desde_observacion(contratacion)
        if monto <= 0:
            continue

        cliente_name = cliente_map.get(contratacion.id_contratacion) or _cliente_nombre_desde_observacion(contratacion) or "Cliente"
        fecha_item = contratacion.fecha_solicitud.strftime("%Y-%m-%d") if contratacion.fecha_solicitud else (
            contratacion.fecha.strftime("%Y-%m-%d") if contratacion.fecha else "-"
        )
        items.append(
            {
                "cliente": cliente_name,
                "fecha": fecha_item,
                "monto": monto,
                "servicio": contratacion.servicio.nombre if contratacion.servicio else "Servicio",
                "inicial": (cliente_name[:1] or "C").upper(),
                "_sort": contratacion.fecha_solicitud or contratacion.fecha,
            }
        )
        total += monto
        count += 1

    items.sort(key=lambda item: item.get("_sort") or timezone.localdate(), reverse=True)
    for item in items:
        item.pop("_sort", None)

    return total, count, items[:limite]


def prestador_home(request):
    prestador = Prestador.objects.filter(usuario=request.usuario).first()
    servicios_qs = _get_or_create_prestador_services(prestador)
    servicios_activos = servicios_qs.count() if prestador else 0
    contrataciones = Contratacion.objects.filter(prestador=prestador) if prestador else Contratacion.objects.none()
    proximas = _proximas_contrataciones_visibles(prestador, 4)
    califs = Calificacion.objects.filter(prestador=prestador) if prestador else Calificacion.objects.none()
    promedio = califs.aggregate(avg=Avg("puntuacion")).get("avg") or 0
    ganancias, _, _ = _ganancias_prestador_data(prestador, limite=0)

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
        categorias_count = prestador.categorias.count() if prestador else 0
        contrataciones_total = (
            Contratacion.objects.filter(prestador=prestador).count() if prestador else 0
        )
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
                "categorias_count": categorias_count,
                "contrataciones_total": contrataciones_total,
            },
        )
    if page == "ganancias":
        prestador = Prestador.objects.filter(usuario=request.usuario).first()
        total, count, pagos = _ganancias_prestador_data(prestador)
        promedio = int(total / count) if count else 0

        return render(
            request,
            "prestador/ganancias.html",
            {
                "total": int(total),
                "count": count,
                "promedio": promedio,
                "pagos": pagos,
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
        servicio = (
            Servicio.objects.select_related("categoria")
            .filter(id_servicio=servicio_id, activo=1)
            .filter(Q(prestador__isnull=True) | Q(prestador=prestador))
            .first()
        )
    if servicio is None:
        servicio = _get_or_create_prestador_services(prestador).first()

    if servicio is None:
        return _json_error("Servicio no encontrado", status=404)

    if not PrestadorCategoria.objects.filter(prestador=prestador, categoria=servicio.categoria).exists():
        return _json_error("Servicio no encontrado", status=404)

    if descripcion:
        prestador.descripcion = descripcion
    if descripcion:
        prestador.save(update_fields=["descripcion"])
    update_fields = []
    if precio_min:
        try:
            servicio.precio_min = float(precio_min)
            update_fields.append("precio_min")
        except ValueError:
            pass
    if precio_max:
        try:
            servicio.precio_max = float(precio_max)
            update_fields.append("precio_max")
        except ValueError:
            pass
    if update_fields:
        servicio.save(update_fields=update_fields)

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
    cliente_map = _cliente_nombre_map(contrataciones)
    now = timezone.now()

    pendientes = []
    aceptadas = []
    eventos = []
    for c in contrataciones:
        estado = (c.estado or "").lower()
        if "rechaz" in estado or "cancel" in estado:
            continue

        expirada = _contratacion_esta_expirada(c, now=now)
        cliente_name = cliente_map.get(c.id_contratacion) or _cliente_nombre_desde_observacion(c)

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

        if not expirada and "pend" in estado:
            pendientes.append(item)
        elif not expirada:
            aceptadas.append(item)

        if c.fecha:
            if expirada:
                color = "#8a8a8a"
            elif "confirm" in estado or "acept" in estado or "proceso" in estado or "activo" in estado:
                color = "#4CAF50"
            else:
                color = "#29B6F6"
            eventos.append({
                "title": item["servicio"],
                "start": str(c.fecha),
                "backgroundColor": color,
                "borderColor": color,
                "textColor": "white",
            })

    return JsonResponse({"pendientes": pendientes, "aceptadas": aceptadas, "eventos": eventos})

def prestador_agenda_aceptar(request, id):
    Contratacion.objects.filter(id_contratacion=id).update(estado="Confirmado")
    return JsonResponse({"ok": True})

def prestador_agenda_rechazar(request, id):
    Contratacion.objects.filter(id_contratacion=id).update(estado="Rechazado")
    return JsonResponse({"ok": True})
