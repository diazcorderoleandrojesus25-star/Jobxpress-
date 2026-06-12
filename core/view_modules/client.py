from .common import *


def cliente_home(request):
    categorias = Categoria.objects.filter(activo=1).order_by("nombre")
    filtro_categoria = _clean_filter(request.GET.get("categoria"))
    servicios_qs = Servicio.objects.filter(activo=1).select_related("categoria", "prestador__usuario")
    if filtro_categoria:
        servicios_qs = servicios_qs.filter(categoria_id=filtro_categoria)

    mapping = {
        "plomeria": ["plomer"],
        "electricidad": ["electric"],
        "carpinteria": ["carpinter"],
        "limpiezagen": ["limpieza"],
        "soportetec": ["soporte", "tecnico", "técnico"],
        "instalacionnequi": ["instalacion", "instalación"],
        "fisioterapia": ["fisioterapia"],
        "salud": ["salud"],
        "asesorias": ["asesor", "tutor"],
        "cuidaranimales": ["cuidad", "animal", "mascota"],
        "redaccion": ["redaccion", "redacción", "contenido"],
        "marketing": ["marketing", "digital"],
    }
    active_pages = set()
    for page_key, keywords in mapping.items():
        q = Q()
        for kw in keywords:
            q |= Q(nombre__icontains=kw)
        if servicios_qs.filter(q).exists():
            active_pages.add(page_key)

    return render(
        request,
        "cliente/home.html",
        {
            "active_pages": active_pages,
            "categorias": categorias,
            "filtroCategoria": filtro_categoria,
        },
    )

def cliente_perfil(request):
    return render(request, "cliente/perfil.html", {"usuario": request.usuario})

def cliente_perfil_actualizar(request):
    usuario = request.usuario
    telefono = _normalize_phone(request.POST.get("telefono", usuario.telefono))
    direccion = _normalize_address(request.POST.get("direccion", usuario.direccion))

    if not _is_valid_phone(telefono):
        return redirect("/cliente/perfil?error=telefono")
    if not _is_valid_address(direccion):
        return redirect("/cliente/perfil?error=direccion")

    usuario.nombre = request.POST.get("nombre", usuario.nombre).strip()
    usuario.email = request.POST.get("email", usuario.email).strip()
    usuario.telefono = telefono
    usuario.direccion = direccion
    usuario.save(update_fields=["nombre", "email", "telefono", "direccion"])
    return redirect("/cliente/perfil?updated=1")

def cliente_dashboard(request):
    cliente = request.usuario
    link_ids = ClienteContratacion.objects.filter(cliente=cliente).values_list(
        "contratacion_id", flat=True
    )
    contrataciones = (
        Contratacion.objects.filter(id_contratacion__in=link_ids)
        .select_related("servicio__categoria", "prestador__usuario")
        .all()
    )

    def _bucket(estado: str | None) -> str:
        if not estado:
            return "otro"
        low = estado.lower()
        if "pend" in low:
            return "pendiente"
        if "cancel" in low:
            return "cancelado"
        if "complet" in low or "final" in low or "termin" in low:
            return "completado"
        if "proceso" in low or "activo" in low:
            return "proceso"
        return "otro"

    total = contrataciones.count()
    counts = {"pendiente": 0, "cancelado": 0, "completado": 0, "proceso": 0, "otro": 0}
    for c in contrataciones:
        counts[_bucket(getattr(c, "estado", None))] += 1

    servicios_distintos = (
        contrataciones.values_list("servicio_id", flat=True).distinct().count()
        if total
        else 0
    )
    prestadores_distintos = (
        contrataciones.values_list("prestador_id", flat=True).distinct().count()
        if total
        else 0
    )

    # Estados (para grafico)
    estado_labels = ["Pendiente", "En proceso", "Completado", "Cancelado", "Otro"]
    estado_values = [
        counts["pendiente"],
        counts["proceso"],
        counts["completado"],
        counts["cancelado"],
        counts["otro"],
    ]

    # Top servicios solicitados
    servicios = (
        contrataciones.values("servicio__nombre")
        .annotate(total=Count("id_contratacion"))
        .order_by("-total")
    )
    top_serv_labels = [s["servicio__nombre"] or "Sin servicio" for s in servicios][:6]
    top_serv_values = [s["total"] for s in servicios][:6]

    # Gasto mensual (COP) desde pagos
    pagos = Pago.objects.filter(contratacion_id__in=link_ids)
    gasto_map: dict[str, float] = {}
    for p in pagos:
        fecha = p.fecha
        if not fecha:
            continue
        key = f"{fecha.year}-{fecha.month:02d}"
        gasto_map[key] = gasto_map.get(key, 0.0) + float(p.monto or 0)
    gasto_sorted = sorted(gasto_map.keys())
    gasto_labels = gasto_sorted[-6:]
    gasto_values = [round(gasto_map[m], 2) for m in gasto_labels]

    # recientes
    recientes = sorted(
        contrataciones,
        key=lambda x: (x.fecha or getattr(x, "fecha_solicitud", None) or timezone.now().date()),
        reverse=True,
    )[:6]

    return render(
        request,
        "cliente/dashboard.html",
        {
            "total_contrataciones": total,
            "servicios_distintos": servicios_distintos,
            "prestadores_distintos": prestadores_distintos,
            "pendientes": counts["pendiente"],
            "canceladas": counts["cancelado"],
            "completadas": counts["completado"],
            "en_proceso": counts["proceso"],
            "estado_labels": estado_labels,
            "estado_values": estado_values,
            "top_serv_labels": top_serv_labels,
            "top_serv_values": top_serv_values,
            "gasto_labels": gasto_labels,
            "gasto_values": gasto_values,
            "recientes": recientes,
        },
    )

def cliente_historial(request):
    cliente = request.usuario
    link_ids = ClienteContratacion.objects.filter(cliente=cliente).values_list("contratacion_id", flat=True)
    contrataciones = (
        Contratacion.objects.filter(id_contratacion__in=list(link_ids))
        .select_related("servicio", "prestador__usuario")
        .order_by("-fecha_solicitud")
    )
    now = timezone.now()

    for contratacion in contrataciones:
        _apply_auto_contratacion_estado(contratacion, now=now)

    # Map calificaciones del cliente por contratacion
    calif_map = {}
    if contrataciones:
        califs = Calificacion.objects.filter(contratacion__in=contrataciones)
        for c in califs:
            link = ClienteCalificacion.objects.filter(calificacion=c).select_related("cliente").first()
            if link and link.cliente_id == cliente.id_usuario:
                calif_map[c.contratacion_id] = c

    historial = []
    for c in contrataciones:
        obs = _parse_observacion(c.observacion)
        prestador_name = "Prestador"
        if c.prestador and c.prestador.usuario:
            prestador_name = f"{c.prestador.usuario.nombre} {c.prestador.usuario.apellido}"

        estado = c.estado or ""
        estado_low = estado.lower()
        prestador_acepto = (
            any(k in estado_low for k in ["confirm", "acept", "complet", "final", "proceso", "activo"])
            and "rechaz" not in estado_low
        )

        calif = calif_map.get(c.id_contratacion)
        historial.append({
            "id": c.id_contratacion,
            "prestador": prestador_name,
            "prestadorId": c.prestador_id,
            "fotoUrl": _media_url(getattr(getattr(c.prestador, "usuario", None), "foto_perfil", None)),
            "fecha": str(c.fecha) if c.fecha else "",
            "hora": obs.get("hora", ""),
            "monto": obs.get("monto", ""),
            "descripcion": obs.get("descripcion", ""),
            "estado": estado or "Pendiente",
            "prestadorAcepto": prestador_acepto,
            "calificacionId": calif.id_calificacion if calif else None,
            "calificacion": calif.puntuacion if calif else None,
            "comentario": calif.comentario if calif else "",
        })

    paginator = Paginator(historial, 4)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "cliente/historial.html",
        {
            "historial_json": json.dumps(list(page_obj.object_list), ensure_ascii=False),
            "cliente_nombre": f"{cliente.nombre} {cliente.apellido}",
            "page_obj": page_obj,
        },
    )

def cliente_historial_eliminar(request, id):
    link = (
        ClienteContratacion.objects.filter(cliente=request.usuario, contratacion_id=id)
        .select_related("contratacion")
        .first()
    )
    if not link:
        return JsonResponse({"error": "Contratacion no encontrada en tu historial."}, status=404)

    link.delete()
    return JsonResponse({"ok": True, "idContratacion": id})

def cliente_chat(request):
    return render(request, "cliente/chatcliente.html")

def cliente_servicio_page(request, page):
    servicio_id = None
    servicio_nombre = page

    # Buscar servicio por categoria o por nombre
    page_aliases = {
        "limpiezagen": ["limpieza", "general"],
        "soportetec": ["soporte", "tecnico", "técnico"],
        "instalacionnequi": ["instalacion", "instalación"],
        "cuidaranimales": ["cuidad", "animal", "mascota"],
        "asesorias": ["asesor", "tutor"],
        "marketing": ["marketing", "digital"],
    }
    def _slug(text: str) -> str:
        import unicodedata
        text = unicodedata.normalize("NFD", text)
        text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
        text = "".join(ch for ch in text.lower() if ch.isalnum())
        return text

    keywords = [page]
    if page in page_aliases:
        keywords = page_aliases[page]

    q_servicio = Q()
    for kw in keywords:
        q_servicio |= Q(nombre__icontains=kw)

    q_categoria = Q()
    for kw in keywords:
        q_categoria |= Q(nombre__icontains=kw)

    categoria = Categoria.objects.filter(activo=1).filter(q_categoria).first()
    servicio = Servicio.objects.filter(activo=1).filter(q_servicio).select_related("categoria").first()
    if servicio is None:
        # Fallback: comparar por slug (ej: "Limpieza General" -> "limpiezageneral")
        page_slug = _slug(page)
        for s in Servicio.objects.filter(activo=1).select_related("categoria"):
            if _slug(s.nombre) == page_slug or page_slug in _slug(s.nombre):
                servicio = s
                break
    if servicio is None and categoria:
        servicio = Servicio.objects.filter(categoria=categoria, activo=1).first()
    if servicio and not categoria:
        categoria = servicio.categoria

    if not servicio:
        return render(request, "cliente/servicio_no_disponible.html", status=404)
    if servicio:
        servicio_id = servicio.id_servicio
        servicio_nombre = servicio.nombre

    if servicio:
        servicios_page = Servicio.objects.filter(activo=1, nombre__iexact=servicio.nombre)
    else:
        servicios_page = Servicio.objects.filter(activo=1)
        if categoria:
            servicios_page = servicios_page.filter(categoria=categoria)
        else:
            servicios_page = servicios_page.filter(nombre__icontains=page)

    prestadores_db = []
    for _s in servicios_page.select_related("prestador", "prestador__usuario"):
        if _s.prestador and _s.prestador not in prestadores_db:
            prestadores_db.append(_s.prestador)

    prestador_ids = [p.id_prestador for p in prestadores_db]
    calificaciones = {
        row["prestador_id"]: row
        for row in Calificacion.objects.filter(prestador_id__in=prestador_ids)
        .values("prestador_id")
        .annotate(promedio=Avg("puntuacion"), total=Count("id_calificacion"))
    }

    for _p in prestadores_db:
        tel = (_p.usuario.telefono or "") if getattr(_p, "usuario", None) else ""
        digits = "".join([c for c in tel if c.isdigit()])
        if len(digits) == 10:
            digits = "57" + digits
        _p.whatsapp = digits
        _p.foto_url = _media_url(getattr(getattr(_p, "usuario", None), "foto_perfil", None))
        rating = calificaciones.get(_p.id_prestador, {})
        promedio = rating.get("promedio") or 0
        _p.promedio_calificacion = round(promedio, 1) if promedio else 0
        _p.total_calificaciones = rating.get("total") or 0


    return render(
        request,
        f"cliente/{page}.html",
        {
            "servicio_id": servicio_id,
            "servicio_nombre": servicio_nombre,
            "prestadores_db": prestadores_db,
        },
    )

def cliente_solicitud(request):
    payload = _parse_body(request)
    prestador_id = payload.get("prestador_id")
    servicio_nombre = (payload.get("servicio") or "").strip()

    prestador = None
    if prestador_id:
        prestador = Prestador.objects.filter(id_prestador=prestador_id).first()
    if prestador is None:
        prestador = Prestador.objects.first()

    if prestador is None:
        return _json_error("No hay prestadores disponibles", status=400)

    servicio = None
    if payload.get("servicio_id"):
        servicio = Servicio.objects.filter(id_servicio=payload.get("servicio_id")).first()
    if servicio is None and servicio_nombre:
        servicio = Servicio.objects.filter(nombre__icontains=servicio_nombre).first()
    if servicio is None:
        servicio = Servicio.objects.first()

    if servicio is None:
        return _json_error("No hay servicios disponibles", status=400)
    if getattr(servicio, "activo", 1) == 0 or getattr(servicio.categoria, "activo", 1) == 0:
        return _json_error("El servicio no esta disponible", status=400)

    fecha = payload.get("fecha")
    hora = payload.get("hora")
    monto = payload.get("monto")
    direccion = payload.get("direccion")
    descripcion = payload.get("descripcion")

    observacion = json.dumps(
        {
            "direccion": direccion,
            "descripcion": descripcion,
            "hora": hora,
            "monto": monto,
        },
        ensure_ascii=False,
    )

    contratacion = Contratacion.objects.create(
        fecha=fecha or None,
        fecha_solicitud=timezone.now().date(),
        estado="Pendiente",
        observacion=observacion,
        prestador=prestador,
        servicio=servicio,
    )

    ClienteContratacion.objects.create(cliente=request.usuario, contratacion=contratacion)
    return JsonResponse({"idContratacion": contratacion.id_contratacion}, status=201)
