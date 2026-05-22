from .common import *


def admin_dashboard(request):
    total_usuarios = Usuario.objects.count()
    usd_cop = None
    try:
        with urllib.request.urlopen("https://api.exchangerate.host/latest?base=USD&symbols=COP", timeout=5) as resp:
            data = json.load(resp)
            usd_cop = data.get("rates", {}).get("COP")
    except Exception:
        usd_cop = None
    prestadores_activos = Prestador.objects.count()
    servicios_publicados = Servicio.objects.count()
    # Sumar montos de contrataciones confirmadas/completadas desde observacion
    total_obs = 0.0
    for c in Contratacion.objects.all():
        estado = (c.estado or "").lower()
        if "confirm" in estado or "complet" in estado:
            obs = _parse_observacion(c.observacion)
            try:
                total_obs += float(obs.get("monto") or 0)
            except Exception:
                pass
    ganancias_totales = total_obs

    # Usuarios por rol
    roles = Rol.objects.all()
    role_counts = []
    total_roles = 0
    for r in roles:
        count = Usuario.objects.filter(rol=r).count()
        role_counts.append({"rol": r.rol, "count": count})
        total_roles += count
    for item in role_counts:
        item["pct"] = int(round((item["count"] / total_roles) * 100)) if total_roles else 0

    # Totales y estados de contrataciones
    total_contrataciones = Contratacion.objects.count()
    estados = {"pendiente": 0, "proceso": 0, "completado": 0, "cancelado": 0, "rechazado": 0, "otro": 0}
    for c in Contratacion.objects.all():
        estado = (c.estado or "").lower()
        if "pend" in estado:
            estados["pendiente"] += 1
        elif "cancel" in estado:
            estados["cancelado"] += 1
        elif "rechaz" in estado:
            estados["rechazado"] += 1
        elif "complet" in estado or "final" in estado or "termin" in estado:
            estados["completado"] += 1
        elif "proceso" in estado or "activo" in estado:
            estados["proceso"] += 1
        else:
            estados["otro"] += 1

    # Usuarios activos/inactivos
    usuarios_activos = Usuario.objects.filter(activo=1).count()
    usuarios_inactivos = Usuario.objects.filter(activo=0).count()

    # Servicios activos/inactivos
    try:
        servicios_activos = Servicio.objects.filter(activo=1).count()
        servicios_inactivos = Servicio.objects.filter(activo=0).count()
    except Exception:
        servicios_activos = servicios_publicados
        servicios_inactivos = 0

    # Servicios contratados por semana (ultimos 5 dias con fecha_solicitud)
    today = timezone.now().date()
    days = [today - timedelta(days=i) for i in range(4, -1, -1)]
    day_labels = [d.strftime("%a") for d in days]
    day_counts = []
    for d in days:
        day_counts.append(Contratacion.objects.filter(fecha_solicitud=d).count())

    # Recientes
    recientes = (Contratacion.objects.select_related("servicio", "prestador__usuario")
                 .order_by("-fecha_solicitud", "-id_contratacion")[:6])
    pagos_recientes = Pago.objects.select_related("contratacion").order_by("-fecha")[:6]

    return render(
        request,
        "admin/dashboard.html",
        {
            "total_usuarios": total_usuarios,
            "usuarios_activos": usuarios_activos,
            "usuarios_inactivos": usuarios_inactivos,
            "prestadores_activos": prestadores_activos,
            "servicios_publicados": servicios_publicados,
            "servicios_activos": servicios_activos,
            "servicios_inactivos": servicios_inactivos,
            "ganancias_totales": int(ganancias_totales),
            "usd_cop": usd_cop,
            "role_counts": role_counts,
            "day_labels": day_labels,
            "day_counts": day_counts,
            "total_contrataciones": total_contrataciones,
            "estados": estados,
            "recientes": recientes,
            "pagos_recientes": pagos_recientes,
        },
    )

def admin_index(request):
    return redirect("/admin/dashboard")

def admin_contrataciones_lista(request):
    filtro_id = _clean_filter(request.GET.get("id"))
    filtro_estado = _clean_filter(request.GET.get("estado", ""))
    filtro_mes = _clean_filter(request.GET.get("mes", ""))

    contrataciones_qs = (
        Contratacion.objects.select_related("servicio", "prestador__usuario")
        .order_by("-fecha_solicitud", "-id_contratacion")
    )
    if filtro_id:
        contrataciones_qs = contrataciones_qs.filter(id_contratacion=filtro_id)
    if filtro_estado:
        contrataciones_qs = contrataciones_qs.filter(estado__icontains=filtro_estado)
    if filtro_mes:
        try:
            year_str, month_str = filtro_mes.split("-")
            contrataciones_qs = contrataciones_qs.filter(
                fecha_solicitud__year=int(year_str),
                fecha_solicitud__month=int(month_str),
            )
        except Exception:
            pass

    cliente_links = (
        ClienteContratacion.objects.filter(contratacion__in=contrataciones_qs)
        .select_related("cliente")
    )
    cliente_map = {}
    for link in cliente_links:
        if link.cliente:
            cliente_map[link.contratacion_id] = f"{link.cliente.nombre} {link.cliente.apellido}"

    total = contrataciones_qs.count()
    pendientes = contrataciones_qs.filter(estado__icontains="pend").count()
    confirmadas = contrataciones_qs.filter(estado__icontains="confirm").count()
    completadas = contrataciones_qs.filter(estado__icontains="complet").count()
    canceladas = contrataciones_qs.filter(estado__icontains="cancel").count()
    rechazadas = contrataciones_qs.filter(estado__icontains="rechaz").count()

    paginator = Paginator(contrataciones_qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    contrataciones = []
    total_monto = 0.0
    for c in contrataciones_qs:
        obs = _parse_observacion(c.observacion)
        monto_raw = obs.get("monto", "")
        estado_low = (c.estado or "").lower()
        if "confirm" in estado_low or "complet" in estado_low:
            try:
                total_monto += float(monto_raw or 0)
            except Exception:
                pass
        cliente_nombre = cliente_map.get(c.id_contratacion, "Cliente")
        prestador_nombre = "Prestador"
        if c.prestador and c.prestador.usuario:
            prestador_nombre = f"{c.prestador.usuario.nombre} {c.prestador.usuario.apellido}"

    for c in page_obj:
        obs = _parse_observacion(c.observacion)
        monto_raw = obs.get("monto", "")
        cliente_nombre = cliente_map.get(c.id_contratacion, "Cliente")
        prestador_nombre = "Prestador"
        if c.prestador and c.prestador.usuario:
            prestador_nombre = f"{c.prestador.usuario.nombre} {c.prestador.usuario.apellido}"

        contrataciones.append(
            {
                "id": c.id_contratacion,
                "cliente": cliente_nombre,
                "prestador": prestador_nombre,
                "servicio": c.servicio.nombre if c.servicio else "Servicio",
                "fecha": str(c.fecha) if c.fecha else "",
                "fecha_solicitud": str(c.fecha_solicitud) if c.fecha_solicitud else "",
                "estado": c.estado or "",
                "monto": monto_raw,
            }
        )

    return render(
        request,
        "admin/contrataciones.html",
        {
            "contrataciones": contrataciones,
            "filtroId": filtro_id,
            "filtroEstado": filtro_estado,
            "filtroMes": filtro_mes,
            "total_contrataciones": total,
            "pendientes": pendientes,
            "confirmadas": confirmadas,
            "completadas": completadas,
            "canceladas": canceladas,
            "rechazadas": rechazadas,
            "monto_total": f"{total_monto:,.0f}",
            "page_obj": page_obj,
        },
    )

def admin_contrataciones_exportar(request):
    filtro_id = _clean_filter(request.GET.get("id"))
    filtro_estado = _clean_filter(request.GET.get("estado", ""))
    filtro_mes = _clean_filter(request.GET.get("mes", ""))

    contrataciones_qs = (
        Contratacion.objects.select_related("servicio", "prestador__usuario")
        .order_by("-fecha_solicitud", "-id_contratacion")
    )
    if filtro_id:
        contrataciones_qs = contrataciones_qs.filter(id_contratacion=filtro_id)
    if filtro_estado:
        contrataciones_qs = contrataciones_qs.filter(estado__icontains=filtro_estado)
    if filtro_mes:
        try:
            year_str, month_str = filtro_mes.split("-")
            contrataciones_qs = contrataciones_qs.filter(
                fecha_solicitud__year=int(year_str),
                fecha_solicitud__month=int(month_str),
            )
        except Exception:
            pass

    cliente_links = (
        ClienteContratacion.objects.filter(contratacion__in=contrataciones_qs)
        .select_related("cliente")
    )
    cliente_map = {}
    for link in cliente_links:
        if link.cliente:
            cliente_map[link.contratacion_id] = f"{link.cliente.nombre} {link.cliente.apellido}"

    total = contrataciones_qs.count()
    pendientes = contrataciones_qs.filter(estado__icontains="pend").count()
    confirmadas = contrataciones_qs.filter(estado__icontains="confirm").count()
    completadas = contrataciones_qs.filter(estado__icontains="complet").count()
    canceladas = contrataciones_qs.filter(estado__icontains="cancel").count()
    rechazadas = contrataciones_qs.filter(estado__icontains="rechaz").count()

    total_monto = 0.0
    rows = []
    for c in contrataciones_qs:
        obs = _parse_observacion(c.observacion)
        monto_raw = obs.get("monto", "")
        estado_low = (c.estado or "").lower()
        if "confirm" in estado_low or "complet" in estado_low:
            try:
                total_monto += float(monto_raw or 0)
            except Exception:
                pass
        cliente_nombre = cliente_map.get(c.id_contratacion, "Cliente")
        prestador_nombre = "Prestador"
        if c.prestador and c.prestador.usuario:
            prestador_nombre = f"{c.prestador.usuario.nombre} {c.prestador.usuario.apellido}"

        rows.append(
            [
                str(c.id_contratacion),
                cliente_nombre,
                prestador_nombre,
                c.servicio.nombre if c.servicio else "Servicio",
                str(c.fecha) if c.fecha else "",
                c.estado or "",
                str(monto_raw),
            ]
        )

    stats = [
        ("Total contrataciones", str(total)),
        ("Pendientes", str(pendientes)),
        ("Confirmadas", str(confirmadas)),
        ("Completadas", str(completadas)),
        ("Canceladas", str(canceladas)),
        ("Rechazadas", str(rechazadas)),
        ("Monto total (COP)", f"{total_monto:,.0f}"),
    ]
    servicios_stats = (
        contrataciones_qs.values("servicio__nombre")
        .annotate(total=Count("id_contratacion"))
        .order_by("-total", "servicio__nombre")[:6]
    )

    return build_report_with_stats(
        title="Reporte de Contrataciones",
        headers=["ID", "Cliente", "Prestador", "Servicio", "Fecha", "Estado", "Monto"],
        rows=rows,
        filename="contrataciones.pdf",
        stats=stats,
        chart_data=[
            {
                "title": "Contrataciones por estado",
                "labels": ["Pendiente", "Confirmada", "Completada", "Cancelada", "Rechazada"],
                "values": [pendientes, confirmadas, completadas, canceladas, rechazadas],
                "type": "pie",
            },
            {
                "title": "Servicios con mas contrataciones",
                "labels": [item["servicio__nombre"] or "Servicio" for item in servicios_stats],
                "values": [item["total"] for item in servicios_stats],
                "type": "bar",
            },
        ],
    )

def admin_categorias_lista(request):
    filtro_id = _clean_filter(request.GET.get("id"))
    filtro_nombre = _clean_filter(request.GET.get("nombre", ""))
    categorias_qs = Categoria.objects.all()
    if filtro_id:
        categorias_qs = categorias_qs.filter(id_categoria=filtro_id)
    if filtro_nombre:
        categorias_qs = categorias_qs.filter(nombre__icontains=filtro_nombre)

    paginator = Paginator(categorias_qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "categorias/lista.html",
        {
            "categorias": page_obj,
            "page_obj": page_obj,
            "filtroId": filtro_id,
            "filtroNombre": filtro_nombre,
        },
    )

def admin_categorias_crear(request):
    if request.method == "GET":
        return render(request, "categorias/crear.html")

    nombre = request.POST.get("nombre")
    Categoria.objects.create(nombre=nombre, activo=1)
    messages.success(request, "Categoria creada correctamente.")
    return redirect("/admin/categorias/lista")

def admin_categorias_editar(request, id):
    categoria = Categoria.objects.filter(id_categoria=id).first()
    if not categoria:
        return redirect("/admin/categorias/lista")

    if request.method == "GET":
        return render(request, "categorias/editar.html", {"categoria": categoria})

    categoria.nombre = request.POST.get("nombre", categoria.nombre)
    categoria.save(update_fields=["nombre"])
    messages.success(request, "Categoria actualizada correctamente.")
    return redirect("/admin/categorias/lista")

def admin_categorias_eliminar(request, id):
    Categoria.objects.filter(id_categoria=id).update(activo=0)
    messages.success(request, "Categoria desactivada.")
    return redirect("/admin/categorias/lista")

def admin_categorias_activar(request, id):
    Categoria.objects.filter(id_categoria=id).update(activo=1)
    messages.success(request, "Categoria activada.")
    return redirect("/admin/categorias/lista")

def admin_categorias_exportar(request):
    filtro_id = _clean_filter(request.GET.get("id"))
    filtro_nombre = _clean_filter(request.GET.get("nombre", ""))
    categorias = Categoria.objects.all()
    if filtro_id:
        categorias = categorias.filter(id_categoria=filtro_id)
    if filtro_nombre:
        categorias = categorias.filter(nombre__icontains=filtro_nombre)

    total = categorias.count()
    activas = categorias.filter(activo=1).count()
    inactivas = categorias.filter(activo=0).count()
    categorias_con_servicios = (
        categorias.annotate(total_servicios=Count("servicio"))
        .order_by("-total_servicios", "nombre")[:6]
    )

    rows = [
        [str(c.id_categoria), c.nombre, "Activa" if c.activo == 1 else "Inactiva"]
        for c in categorias
    ]
    return build_report_with_stats(
        title="Reporte de Categorias",
        headers=["ID", "Nombre", "Estado"],
        rows=rows,
        filename="categorias.pdf",
        stats=[
            ("Total de categorias", str(total)),
            ("Activas", str(activas)),
            ("Inactivas", str(inactivas)),
        ],
        chart_data=[
            {
                "title": "Estado de categorias",
                "labels": ["Activas", "Inactivas"],
                "values": [activas, inactivas],
                "type": "pie",
            },
            {
                "title": "Servicios por categoria",
                "labels": [c.nombre for c in categorias_con_servicios],
                "values": [c.total_servicios for c in categorias_con_servicios],
                "type": "bar",
            },
        ],
    )

def admin_roles_lista(request):
    filtro_id = _clean_filter(request.GET.get("id"))
    filtro_nombre = _clean_filter(request.GET.get("nombre", ""))
    roles_qs = Rol.objects.all()
    if filtro_id:
        roles_qs = roles_qs.filter(id_rol=filtro_id)
    if filtro_nombre:
        roles_qs = roles_qs.filter(rol__icontains=filtro_nombre)

    paginator = Paginator(roles_qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "roles/lista.html",
        {
            "roles": page_obj,
            "page_obj": page_obj,
            "filtroId": filtro_id,
            "filtroNombre": filtro_nombre,
        },
    )

def admin_roles_crear(request):
    if request.method == "GET":
        return render(request, "roles/crear.html")
    rol = request.POST.get("rol")
    Rol.objects.create(rol=rol)
    messages.success(request, "Rol creado correctamente.")
    return redirect("/admin/roles/lista")

def admin_roles_editar(request, id):
    rol = Rol.objects.filter(id_rol=id).first()
    if not rol:
        return redirect("/admin/roles/lista?error=NoExiste")

    if request.method == "GET":
        return render(request, "roles/editar.html", {"rol": rol})

    rol.rol = request.POST.get("rol", rol.rol)
    rol.save(update_fields=["rol"])
    messages.success(request, "Rol actualizado correctamente.")
    return redirect("/admin/roles/lista")

def admin_roles_eliminar(request, id):
    Rol.objects.filter(id_rol=id).delete()
    messages.success(request, "Rol eliminado.")
    return redirect("/admin/roles/lista")

def admin_roles_exportar(request):
    filtro_id = _clean_filter(request.GET.get("id"))
    filtro_nombre = _clean_filter(request.GET.get("nombre", ""))
    roles = Rol.objects.all()
    if filtro_id:
        roles = roles.filter(id_rol=filtro_id)
    if filtro_nombre:
        roles = roles.filter(rol__icontains=filtro_nombre)

    roles_con_usuarios = roles.annotate(total_usuarios=Count("usuario")).order_by("-total_usuarios", "rol")
    rows = [[str(r.id_rol), r.rol, str(r.total_usuarios)] for r in roles_con_usuarios]
    return build_report_with_stats(
        title="Reporte de Roles",
        headers=["ID", "Rol", "Usuarios asociados"],
        rows=rows,
        filename="roles.pdf",
        stats=[
            ("Total de roles", str(roles.count())),
            ("Usuarios asignados", str(sum(r.total_usuarios for r in roles_con_usuarios))),
            ("Rol con mas usuarios", roles_con_usuarios[0].rol if roles_con_usuarios else "-"),
        ],
        chart_data={
            "title": "Usuarios por rol",
            "labels": [r.rol for r in roles_con_usuarios[:6]],
            "values": [r.total_usuarios for r in roles_con_usuarios[:6]],
            "type": "bar",
        },
    )

def admin_servicios_lista(request):
    filtro_id = _clean_filter(request.GET.get("id"))
    filtro_nombre = _clean_filter(request.GET.get("nombre", ""))
    filtro_categoria = _clean_filter(request.GET.get("idCategoria"))
    servicios_qs = Servicio.objects.select_related("categoria").all().order_by("id_servicio")

    if filtro_id:
        servicios_qs = servicios_qs.filter(id_servicio=filtro_id)
    if filtro_nombre:
        servicios_qs = servicios_qs.filter(nombre__icontains=filtro_nombre)
    if filtro_categoria:
        servicios_qs = servicios_qs.filter(categoria_id=filtro_categoria)

    paginator = Paginator(servicios_qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "servicios/lista.html",
        {
            "servicios": page_obj,
            "page_obj": page_obj,
            "categorias": Categoria.objects.all(),
            "filtroId": filtro_id,
            "filtroNombre": filtro_nombre,
            "filtroIdCategoria": filtro_categoria,
        },
    )

def admin_servicios_crear(request):
    if request.method == "GET":
        return render(request, "servicios/crear.html", {"categorias": Categoria.objects.all()})

    nombre = request.POST.get("nombre")
    descripcion = request.POST.get("descripcion")
    precio_min = request.POST.get("precio_min")
    precio_max = request.POST.get("precio_max")
    id_categoria = request.POST.get("categoria_id") or request.POST.get("categoria")

    categoria = Categoria.objects.filter(id_categoria=id_categoria).first()
    if categoria:
        Servicio.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            precio_min=precio_min or 0,
            precio_max=precio_max or 0,
            activo=1,
            categoria=categoria,
        )

    messages.success(request, "Servicio creado correctamente.")
    return redirect("/admin/servicios/lista")

def admin_servicios_editar(request, id):
    servicio = Servicio.objects.filter(id_servicio=id).first()
    if not servicio:
        return redirect("/admin/servicios/lista")

    if request.method == "GET":
        return render(
            request,
            "servicios/editar.html",
            {"servicio": servicio, "categorias": Categoria.objects.all()},
        )

    servicio.nombre = request.POST.get("nombre", servicio.nombre)
    servicio.descripcion = request.POST.get("descripcion", servicio.descripcion)
    servicio.precio_min = request.POST.get("precio_min", servicio.precio_min)
    servicio.precio_max = request.POST.get("precio_max", servicio.precio_max)
    activo_val = request.POST.get("activo")
    if activo_val in ("0","1"):
        servicio.activo = int(activo_val)
    id_categoria = request.POST.get("categoria_id") or request.POST.get("categoria")
    if id_categoria:
        categoria = Categoria.objects.filter(id_categoria=id_categoria).first()
        if categoria:
            servicio.categoria = categoria
    servicio.save()
    messages.success(request, "Servicio actualizado correctamente.")
    return redirect("/admin/servicios/lista")

def admin_servicios_eliminar(request, id):
    Servicio.objects.filter(id_servicio=id).update(activo=0)
    messages.success(request, "Servicio desactivado.")
    return redirect("/admin/servicios/lista")

def admin_servicios_activar(request, id):
    Servicio.objects.filter(id_servicio=id).update(activo=1)
    messages.success(request, "Servicio activado.")
    return redirect("/admin/servicios/lista")

def admin_servicios_exportar(request):
    filtro_id = _clean_filter(request.GET.get("id"))
    filtro_nombre = _clean_filter(request.GET.get("nombre", ""))
    filtro_categoria = _clean_filter(request.GET.get("idCategoria"))

    servicios = Servicio.objects.select_related("categoria", "prestador__usuario").all()
    if filtro_id:
        servicios = servicios.filter(id_servicio=filtro_id)
    if filtro_nombre:
        servicios = servicios.filter(nombre__icontains=filtro_nombre)
    if filtro_categoria:
        servicios = servicios.filter(categoria_id=filtro_categoria)

    total = servicios.count()
    activos = servicios.filter(activo=1).count()
    inactivos = servicios.filter(activo=0).count()
    precios = servicios.aggregate(avg_min=Avg("precio_min"), avg_max=Avg("precio_max"))
    avg_min = precios.get("avg_min") or 0
    avg_max = precios.get("avg_max") or 0

    rows = [
        [
            str(s.id_servicio),
            s.nombre,
            s.descripcion,
            s.categoria.nombre if s.categoria else "-",
            str(s.precio_min),
            str(s.precio_max),
        ]
        for s in servicios
    ]
    stats = [
        ("Total de servicios", str(total)),
        ("Activos", str(activos)),
        ("Inactivos", str(inactivos)),
        ("Promedio precio min", f"{avg_min:,.0f}"),
        ("Promedio precio max", f"{avg_max:,.0f}"),
    ]
    servicios_por_categoria = (
        servicios.values("categoria__nombre")
        .annotate(total=Count("id_servicio"))
        .order_by("-total", "categoria__nombre")[:6]
    )
    return build_report_with_stats(
        title="Reporte de Servicios",
        headers=["ID", "Nombre", "Descripcion", "Categoria", "Precio Min", "Precio Max"],
        rows=rows,
        filename="servicios.pdf",
        stats=stats,
        chart_data=[
            {
                "title": "Estado de servicios",
                "labels": ["Activos", "Inactivos"],
                "values": [activos, inactivos],
                "type": "pie",
            },
            {
                "title": "Servicios por categoria",
                "labels": [item["categoria__nombre"] or "Sin categoria" for item in servicios_por_categoria],
                "values": [item["total"] for item in servicios_por_categoria],
                "type": "bar",
            },
        ],
    )

def admin_servicios_carga(request):
    if request.method != "POST":
        return redirect("/admin/servicios/lista")

    archivo = request.FILES.get("archivo")
    if not archivo:
        return redirect("/admin/servicios/lista?carga_err=Sin archivo")

    try:
        contenido = archivo.read()
        try:
            texto = contenido.decode("utf-8-sig")
        except Exception:
            texto = contenido.decode("latin-1")
    except Exception:
        return redirect("/admin/servicios/lista?carga_err=No se pudo leer el archivo")

    default_categoria = Categoria.objects.first()
    ok = 0
    skip = 0
    err = 0

    try:
        reader = csv.DictReader(io.StringIO(texto))
        fieldnames = [f.strip().lower() for f in (reader.fieldnames or [])]
        has_headers = any(fieldnames)
    except Exception:
        reader = None
        has_headers = False

    def _resolve_categoria(row):
        cat_id = row.get("categoria_id") or row.get("id_categoria")
        if cat_id:
            cat = Categoria.objects.filter(id_categoria=str(cat_id).strip()).first()
            if cat:
                return cat
        cat_name = (row.get("categoria") or row.get("nombre_categoria") or "").strip()
        if cat_name:
            cat = Categoria.objects.filter(nombre__iexact=cat_name).first()
            if cat:
                return cat
        return default_categoria

    def _resolve_prestador(row):
        prest_id = row.get("id_prestador") or row.get("prestador_id")
        if prest_id:
            return Prestador.objects.filter(id_prestador=str(prest_id).strip()).first()
        return None

    def _to_float(val):
        try:
            return float(str(val).replace(",", "."))
        except Exception:
            return 0.0

    def _create_service(data):
        nonlocal ok, skip, err
        nombre = (data.get("nombre") or "").strip()
        if not nombre:
            skip += 1
            return
        categoria = _resolve_categoria(data)
        if not categoria:
            err += 1
            return
        descripcion = (data.get("descripcion") or "").strip()
        precio_min = _to_float(data.get("precio_min") or data.get("precio_minimo") or data.get("min") or 0)
        precio_max = _to_float(data.get("precio_max") or data.get("precio_maximo") or data.get("max") or 0)
        activo = data.get("activo", "1")
        activo_val = 1 if str(activo).strip() in ("1", "true", "True", "activo", "Activo") else 0
        prestador = _resolve_prestador(data)
        Servicio.objects.create(
            nombre=nombre,
            descripcion=descripcion,
            precio_min=precio_min,
            precio_max=precio_max,
            activo=activo_val,
            prestador=prestador,
            categoria=categoria,
        )
        ok += 1

    if has_headers and reader:
        for row in reader:
            try:
                _create_service({k.strip().lower(): v for k, v in row.items()})
            except Exception:
                err += 1
    else:
        # Sin headers: columnas esperadas
        # nombre, descripcion, precio_min, precio_max, categoria, id_prestador, activo
        reader2 = csv.reader(io.StringIO(texto))
        for row in reader2:
            if not row:
                continue
            data = {
                "nombre": row[0] if len(row) > 0 else "",
                "descripcion": row[1] if len(row) > 1 else "",
                "precio_min": row[2] if len(row) > 2 else "",
                "precio_max": row[3] if len(row) > 3 else "",
                "categoria": row[4] if len(row) > 4 else "",
                "id_prestador": row[5] if len(row) > 5 else "",
                "activo": row[6] if len(row) > 6 else "1",
            }
            try:
                _create_service(data)
            except Exception:
                err += 1

    return redirect(f"/admin/servicios/lista?carga_ok={ok}&carga_skip={skip}&carga_err={err}")

def admin_metodos_pago_lista(request):
    filtro_id = _clean_filter(request.GET.get("id"))
    filtro_forma = _clean_filter(request.GET.get("formaPago", ""))
    metodos_qs = MetodoPago.objects.all()
    if filtro_id:
        metodos_qs = metodos_qs.filter(id_metodo_pago=filtro_id)
    if filtro_forma:
        metodos_qs = metodos_qs.filter(forma_pago__icontains=filtro_forma)

    paginator = Paginator(metodos_qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "metodos_pago/lista.html",
        {
            "metodos": page_obj,
            "page_obj": page_obj,
            "filtroId": filtro_id,
            "filtroFormaPago": filtro_forma,
        },
    )

def admin_metodos_pago_crear(request):
    if request.method == "GET":
        return render(request, "metodos_pago/crear.html")
    forma = request.POST.get("forma_pago") or request.POST.get("formaPago")
    MetodoPago.objects.create(forma_pago=forma)
    messages.success(request, "Metodo de pago creado correctamente.")
    return redirect("/admin/metodos_pago/lista")

def admin_metodos_pago_editar(request, id):
    metodo = MetodoPago.objects.filter(id_metodo_pago=id).first()
    if not metodo:
        return redirect("/admin/metodos_pago/lista?error=NoExiste")

    if request.method == "GET":
        return render(request, "metodos_pago/editar.html", {"metodo": metodo})

    metodo.forma_pago = request.POST.get("forma_pago", metodo.forma_pago)
    metodo.save(update_fields=["forma_pago"])
    messages.success(request, "Metodo de pago actualizado correctamente.")
    return redirect("/admin/metodos_pago/lista")

def admin_metodos_pago_eliminar(request, id):
    Pago.objects.filter(metodo_id=id).delete()
    MetodoPago.objects.filter(id_metodo_pago=id).delete()
    messages.success(request, "Metodo de pago eliminado.")
    return redirect("/admin/metodos_pago/lista")

def admin_metodos_pago_exportar(request):
    filtro_id = _clean_filter(request.GET.get("id"))
    filtro_forma = _clean_filter(request.GET.get("formaPago", ""))
    metodos = MetodoPago.objects.all()
    if filtro_id:
        metodos = metodos.filter(id_metodo_pago=filtro_id)
    if filtro_forma:
        metodos = metodos.filter(forma_pago__icontains=filtro_forma)

    metodos_stats = metodos.annotate(total_pagos=Count("pago"), monto_total=Sum("pago__monto")).order_by("-total_pagos", "forma_pago")
    rows = [
        [
            str(m.id_metodo_pago),
            m.forma_pago,
            str(m.total_pagos or 0),
            f"{(m.monto_total or 0):,.0f}",
        ]
        for m in metodos_stats
    ]
    return build_report_with_stats(
        title="Reporte de Metodos de Pago",
        headers=["ID", "Forma de Pago", "Pagos asociados", "Monto total"],
        rows=rows,
        filename="metodos_pago.pdf",
        stats=[
            ("Total de metodos", str(metodos.count())),
            ("Pagos registrados", str(sum((m.total_pagos or 0) for m in metodos_stats))),
            ("Monto total procesado", f"{sum((m.monto_total or 0) for m in metodos_stats):,.0f}"),
        ],
        chart_data=[
            {
                "title": "Uso por metodo de pago",
                "labels": [m.forma_pago for m in metodos_stats[:6]],
                "values": [m.total_pagos or 0 for m in metodos_stats[:6]],
                "type": "bar",
            },
            {
                "title": "Monto por metodo",
                "labels": [m.forma_pago for m in metodos_stats[:6]],
                "values": [float(m.monto_total or 0) for m in metodos_stats[:6]],
                "type": "pie",
            },
        ],
    )

def admin_usuarios_lista(request):
    filtro_id = _clean_filter(request.GET.get("idUsuario"))
    filtro_nombre = _clean_filter(request.GET.get("nombre", ""))
    filtro_rol = _clean_filter(request.GET.get("idRol"))
    filtro_activo = _clean_filter(request.GET.get("activo"))

    usuarios_qs = Usuario.objects.select_related("rol").order_by("id_usuario")
    if filtro_id:
        usuarios_qs = usuarios_qs.filter(id_usuario=filtro_id)
    if filtro_nombre:
        usuarios_qs = usuarios_qs.filter(nombre__icontains=filtro_nombre)
    if filtro_rol:
        usuarios_qs = usuarios_qs.filter(rol_id=filtro_rol)
    if filtro_activo in ("0", "1"):
        usuarios_qs = usuarios_qs.filter(activo=int(filtro_activo))

    paginator = Paginator(usuarios_qs, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "usuario/lista.html",
        {
            "usuarios": page_obj,
            "page_obj": page_obj,
            "roles": Rol.objects.all(),
            "filtroId": filtro_id,
            "filtroNombre": filtro_nombre,
            "filtroRol": filtro_rol,
            "filtroActivo": filtro_activo,
        },
    )

def admin_usuarios_carga(request):
    if request.method != "POST":
        return redirect("/admin/usuarios/lista")

    archivo = request.FILES.get("archivo")
    if not archivo:
        return redirect("/admin/usuarios/lista?carga_err=Sin archivo")

    try:
        contenido = archivo.read()
        try:
            texto = contenido.decode("utf-8-sig")
        except Exception:
            texto = contenido.decode("latin-1")
    except Exception:
        return redirect("/admin/usuarios/lista?carga_err=No se pudo leer el archivo")

    default_rol = Rol.objects.filter(rol__iexact="ROLE_CLIENTE").first() or Rol.objects.first()
    ok = 0
    skip = 0
    err = 0

    # Intentar con encabezados
    try:
        reader = csv.DictReader(io.StringIO(texto))
        fieldnames = [f.strip().lower() for f in (reader.fieldnames or [])]
        has_headers = any(fieldnames)
    except Exception:
        reader = None
        has_headers = False

    def _resolve_role(row):
        rol_id = row.get("rol_id") or row.get("id_rol")
        if rol_id:
            return Rol.objects.filter(id_rol=str(rol_id).strip()).first()
        rol_name = (row.get("rol") or row.get("role") or "").strip()
        if rol_name:
            return Rol.objects.filter(rol__iexact=rol_name).first()
        return default_rol

    def _create_user(data):
        nonlocal ok, skip, err
        email = (data.get("email") or "").strip().lower()
        if not email:
            skip += 1
            return
        if Usuario.objects.filter(email__iexact=email).exists():
            skip += 1
            return
        rol = _resolve_role(data)
        if not rol:
            err += 1
            return
        raw_pass = (data.get("contrasena") or data.get("password") or "Jobxpress123!").strip()
        activo = data.get("activo", "1")
        activo_val = 1 if str(activo).strip() in ("1", "true", "True", "activo", "Activo") else 0
        Usuario.objects.create(
            nombre=(data.get("nombre") or "").strip(),
            apellido=(data.get("apellido") or "").strip(),
            email=email,
            telefono=(data.get("telefono") or "").strip(),
            direccion=(data.get("direccion") or "").strip(),
            contrasena=_hash_password(raw_pass),
            rol=rol,
            activo=activo_val,
            created_at=timezone.now(),
            updated_at=timezone.now(),
        )
        ok += 1

    if has_headers and reader:
        for row in reader:
            try:
                _create_user({k.strip().lower(): v for k, v in row.items()})
            except Exception:
                err += 1
    else:
        # Sin headers: columnas esperadas
        # nombre, apellido, email, telefono, direccion, rol, contrasena, activo
        reader2 = csv.reader(io.StringIO(texto))
        for row in reader2:
            if not row:
                continue
            data = {
                "nombre": row[0] if len(row) > 0 else "",
                "apellido": row[1] if len(row) > 1 else "",
                "email": row[2] if len(row) > 2 else "",
                "telefono": row[3] if len(row) > 3 else "",
                "direccion": row[4] if len(row) > 4 else "",
                "rol": row[5] if len(row) > 5 else "",
                "contrasena": row[6] if len(row) > 6 else "",
                "activo": row[7] if len(row) > 7 else "1",
            }
            try:
                _create_user(data)
            except Exception:
                err += 1

    return redirect(f"/admin/usuarios/lista?carga_ok={ok}&carga_skip={skip}&carga_err={err}")

def admin_usuarios_crear(request):
    if request.method == "GET":
        return render(request, "usuario/crear.html", {"roles": Rol.objects.all()})

    rol_id = request.POST.get("rol_id") or request.POST.get("rol")
    rol = Rol.objects.filter(id_rol=rol_id).first()
    if not rol:
        return redirect("/admin/usuarios/lista?error=Rol")

    raw_pass = request.POST.get("contrasena", "")
    hashed = _hash_password(raw_pass) if raw_pass else ""

    Usuario.objects.create(
        nombre=request.POST.get("nombre", ""),
        apellido=request.POST.get("apellido", ""),
        email=request.POST.get("email", ""),
        telefono=request.POST.get("telefono", ""),
        direccion=request.POST.get("direccion", ""),
        contrasena=hashed,
        activo=1,
        rol=rol,
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )

    messages.success(request, "Usuario creado correctamente.")
    return redirect("/admin/usuarios/lista")

def admin_usuarios_editar(request, id):
    usuario = Usuario.objects.filter(id_usuario=id).first()
    if not usuario:
        if _wants_json(request):
            return JsonResponse({"error": "Usuario no encontrado."}, status=404)
        return redirect("/admin/usuarios/lista?error=NoExiste")

    if request.method == "GET":
        if _wants_json(request):
            return JsonResponse(
                {
                    "usuario": {
                        "id": usuario.id_usuario,
                        "nombre": usuario.nombre,
                        "apellido": usuario.apellido,
                        "email": usuario.email,
                        "telefono": usuario.telefono,
                        "direccion": usuario.direccion,
                        "rolId": usuario.rol_id if getattr(usuario, "rol_id", None) else "",
                        "activo": usuario.activo,
                    },
                    "roles": [{"id": r.id_rol, "rol": r.rol} for r in Rol.objects.all().order_by("id_rol")],
                }
            )
        return render(request, "usuario/editar.html", {"usuario": usuario, "roles": Rol.objects.all()})

    usuario.nombre = request.POST.get("nombre", usuario.nombre)
    usuario.apellido = request.POST.get("apellido", usuario.apellido)
    usuario.email = request.POST.get("email", usuario.email)
    usuario.telefono = request.POST.get("telefono", usuario.telefono)
    usuario.direccion = request.POST.get("direccion", usuario.direccion)
    nueva = request.POST.get("contrasena")
    if nueva:
        usuario.contrasena = _hash_password(nueva)
    rol_id = request.POST.get("rol_id") or request.POST.get("rol")
    if rol_id:
        rol = Rol.objects.filter(id_rol=rol_id).first()
        if rol:
            usuario.rol = rol

    usuario.updated_at = timezone.now()
    usuario.save()
    if _wants_json(request):
        return JsonResponse(
            {
                "ok": True,
                "usuario": {
                    "id": usuario.id_usuario,
                    "nombre": usuario.nombre,
                    "apellido": usuario.apellido,
                    "email": usuario.email,
                    "telefono": usuario.telefono,
                    "direccion": usuario.direccion,
                    "rol": usuario.rol.rol if usuario.rol else "-",
                    "rolId": usuario.rol_id if getattr(usuario, "rol_id", None) else "",
                    "activo": usuario.activo,
                },
            }
        )
    messages.success(request, "Usuario actualizado correctamente.")
    return redirect("/admin/usuarios/lista")

def admin_usuarios_eliminar(request, id):
    usuario = Usuario.objects.filter(id_usuario=id).first()
    if not usuario:
        if _wants_json(request):
            return JsonResponse({"error": "Usuario no encontrado."}, status=404)
        return redirect("/admin/usuarios/lista")
    usuario.activo = 0
    usuario.save(update_fields=["activo"])
    if _wants_json(request):
        return JsonResponse({"ok": True, "id": usuario.id_usuario, "activo": 0})
    messages.success(request, "Usuario desactivado.")
    return redirect("/admin/usuarios/lista")

def admin_usuarios_activar(request, id):
    usuario = Usuario.objects.filter(id_usuario=id).first()
    if not usuario:
        if _wants_json(request):
            return JsonResponse({"error": "Usuario no encontrado."}, status=404)
        return redirect("/admin/usuarios/lista")
    usuario.activo = 1
    usuario.save(update_fields=["activo"])
    if _wants_json(request):
        return JsonResponse({"ok": True, "id": usuario.id_usuario, "activo": 1})
    messages.success(request, "Usuario activado.")
    return redirect("/admin/usuarios/lista")

def admin_usuarios_exportar(request):
    filtro_id = _clean_filter(request.GET.get("idUsuario"))
    filtro_nombre = _clean_filter(request.GET.get("nombre", ""))
    filtro_rol = _clean_filter(request.GET.get("idRol"))
    filtro_activo = _clean_filter(request.GET.get("activo"))

    usuarios = Usuario.objects.select_related("rol").all()
    if filtro_id:
        usuarios = usuarios.filter(id_usuario=filtro_id)
    if filtro_nombre:
        usuarios = usuarios.filter(nombre__icontains=filtro_nombre)
    if filtro_rol:
        usuarios = usuarios.filter(rol_id=filtro_rol)
    if filtro_activo in ("0", "1"):
        usuarios = usuarios.filter(activo=int(filtro_activo))

    total = usuarios.count()
    activos = usuarios.filter(activo=1).count()
    inactivos = usuarios.filter(activo=0).count()
    roles_stats = usuarios.values("rol__rol").annotate(total=Count("id_usuario")).order_by("-total")
    stats = [
        ("Total de usuarios", str(total)),
        ("Activos", str(activos)),
        ("Inactivos", str(inactivos)),
    ]
    for r in roles_stats:
        if r.get("rol__rol"):
            stats.append((f"Rol {r['rol__rol']}", str(r["total"])))

    rows = [
        [
            str(u.id_usuario),
            u.nombre,
            u.apellido,
            u.email,
            u.telefono,
            u.direccion,
            u.rol.rol if u.rol else "-",
            "Activo" if getattr(u, "activo", 1) == 1 else "Inactivo",
            u.created_at.isoformat(sep=" ") if u.created_at else "-",
            u.updated_at.isoformat(sep=" ") if u.updated_at else "-",
        ]
        for u in usuarios
    ]
    return build_report_with_stats(
        title="Reporte de Usuarios",
        headers=[
            "ID",
            "Nombre",
            "Apellido",
            "Email",
            "Telefono",
            "Direccion",
            "Rol",
            "Estado",
            "Creado",
            "Actualizado",
        ],
        rows=rows,
        filename="usuarios.pdf",
        stats=stats,
        chart_data=[
            {
                "title": "Distribucion por rol",
                "labels": [r["rol__rol"] or "Sin rol" for r in roles_stats[:6]],
                "values": [r["total"] for r in roles_stats[:6]],
                "type": "pie",
            },
            {
                "title": "Estado de usuarios",
                "labels": ["Activos", "Inactivos"],
                "values": [activos, inactivos],
                "type": "bar",
            },
        ],
    )
