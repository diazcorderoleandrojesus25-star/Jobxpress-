from .common import *


def home(request):
    if not getattr(request, "usuario", None):
        return render(request, "index.html")
    return _redirect_by_role(request.rol)

def login_view(request):
    if request.method == "GET":
        return render(request, "login.html")

    email = (request.POST.get("username") or request.POST.get("email") or "").strip()
    password = request.POST.get("password")
    if not email:
        return redirect("/login?error")
    usuario = Usuario.objects.select_related("rol").filter(email__iexact=email).first()

    if usuario is None or not _check_password(password or "", usuario.contrasena):
        return redirect("/login?error")
    if getattr(usuario, "activo", 1) == 0:
        return redirect("/login?error=inactive")

    request.session["usuario_id"] = usuario.id_usuario
    return _redirect_by_role(usuario.rol.rol if usuario.rol else None)

def logout_view(request):
    request.session.flush()
    return redirect("/")

def registro_view(request):
    servicios = Servicio.objects.filter(activo=1).select_related("categoria")
    if request.method == "GET":
        return render(request, "registro.html", {"servicios": servicios})

    nombre = request.POST.get("nombre", "")
    apellido = request.POST.get("apellido", "")
    email = request.POST.get("email", "")
    telefono = request.POST.get("telefono", "")
    direccion = request.POST.get("direccion", "")
    contrasena = request.POST.get("contrasena", "")
    confirmar = request.POST.get("contrasena_confirmation", "")
    id_rol = request.POST.get("id_rol")

    if contrasena != confirmar:
        return render(
            request,
            "registro.html",
            {
                "error": "Las contrasenas no coinciden",
                "nombre": nombre,
                "apellido": apellido,
                "email": email,
                "telefono": telefono,
                "direccion": direccion,
                "servicios": servicios,
            },
        )

    if not PASSWORD_REGEX.match(contrasena):
        return render(
            request,
            "registro.html",
            {
                "error": "La contrasena debe tener mayuscula, numero y simbolo",
                "nombre": nombre,
                "apellido": apellido,
                "email": email,
                "telefono": telefono,
                "direccion": direccion,
                "servicios": servicios,
            },
        )

    if Usuario.objects.filter(email=email).exists():
        return render(
            request,
            "registro.html",
            {
                "error": "El correo ya esta registrado",
                "nombre": nombre,
                "apellido": apellido,
                "email": email,
                "telefono": telefono,
                "direccion": direccion,
                "servicios": servicios,
            },
        )

    rol = Rol.objects.filter(id_rol=id_rol).first()
    if rol is None:
        return render(
            request,
            "registro.html",
            {
                "error": "Rol no encontrado",
                "nombre": nombre,
                "apellido": apellido,
                "email": email,
                "telefono": telefono,
                "direccion": direccion,
                "servicios": servicios,
            },
        )

    servicio_id = request.POST.get("servicio_id")
    prestador_dias_list = [d for d in request.POST.getlist("prestador_dias") if d]
    prestador_hora_inicio = (request.POST.get("prestador_hora_inicio") or "").strip()
    prestador_hora_fin = (request.POST.get("prestador_hora_fin") or "").strip()
    prestador_dias = ", ".join(prestador_dias_list)
    prestador_horario = f"{prestador_hora_inicio} - {prestador_hora_fin}" if prestador_hora_inicio and prestador_hora_fin else ""
    prestador_descripcion = request.POST.get("prestador_descripcion", "").strip()
    if rol.rol == "ROLE_PRESTADOR" and not servicio_id:
        return render(
            request,
            "registro.html",
            {
                "error": "Selecciona un servicio para el prestador",
                "nombre": nombre,
                "apellido": apellido,
                "email": email,
                "telefono": telefono,
                "direccion": direccion,
                "servicios": servicios,
            },
        )
    if rol.rol == "ROLE_PRESTADOR" and (not prestador_dias or not prestador_horario or not prestador_descripcion):
        return render(
            request,
            "registro.html",
            {
                "error": "Completa días, horario y descripción del servicio",
                "nombre": nombre,
                "apellido": apellido,
                "email": email,
                "telefono": telefono,
                "direccion": direccion,
                "servicios": servicios,
            },
        )

    usuario = Usuario.objects.create(
        nombre=nombre,
        apellido=apellido,
        email=email,
        telefono=telefono,
        direccion=direccion,
        contrasena=_hash_password(contrasena),
        rol=rol,
        activo=1,
        created_at=timezone.now(),
        updated_at=timezone.now(),
    )

    if rol.rol == "ROLE_PRESTADOR":
        prestador = Prestador.objects.create(
            usuario=usuario,
            descripcion=prestador_descripcion,
            dias_atencion=prestador_dias,
            horario_atencion=prestador_horario,
        )
        servicio_sel = (
            Servicio.objects.select_related("categoria")
            .filter(id_servicio=servicio_id)
            .first()
        )
        if servicio_sel and servicio_sel.categoria:
            PrestadorCategoria.objects.get_or_create(
                prestador=prestador,
                categoria=servicio_sel.categoria,
            )

            Servicio.objects.create(
                nombre=servicio_sel.nombre,
                descripcion=servicio_sel.descripcion,
                precio_min=servicio_sel.precio_min,
                precio_max=servicio_sel.precio_max,
                activo=1,
                prestador=prestador,
                categoria=servicio_sel.categoria,
            )

    return redirect("/login?registro_ok")

def registro_categorias(request):
    categorias = list(Categoria.objects.all().values("id_categoria", "nombre"))
    return JsonResponse(categorias, safe=False)

def forgot_view(request):
    if request.method == "GET":
        return render(request, "forgot-password.html")

    email = (request.POST.get("email") or "").strip()

    try:
        validate_email(email)
    except ValidationError:
        return render(
            request,
            "forgot-password.html",
            {"error": "Direccion invalida."},
        )

    usuario = Usuario.objects.filter(email__iexact=email).first()
    if not usuario:
        return render(
            request,
            "forgot-password.html",
            {"error": "El correo ingresado no esta registrado."},
        )

    token = str(uuid.uuid4())
    expiration = timezone.now() + timedelta(hours=1)
    PasswordResetToken.objects.create(token=token, usuario=usuario, expiration=expiration)

    reset_url = f"http://localhost:8000/reset?token={token}"
    subject = "Recuperación de contraseña - JobXpress"
    text_body = (
        "Hola,\n\n"
        "Recibimos una solicitud para restablecer tu contraseña en JobXpress.\n"
        f"Usa este enlace para continuar: {reset_url}\n\n"
        "Este enlace estara disponible durante 1 hora.\n"
        "Si no solicitaste este cambio, puedes ignorar este mensaje."
    )
    html = f"""
    <div style="margin:0; padding:32px 18px; background:linear-gradient(180deg,#f7f3ec 0%,#eef3f3 100%); font-family:Arial,sans-serif; color:#1f2a33;">
        <div style="max-width:620px; margin:0 auto; background:#ffffff; border-radius:24px; border:1px solid rgba(111,156,149,0.20); box-shadow:0 18px 40px rgba(31,42,51,0.12); overflow:hidden;">
            <div style="padding:26px 26px 12px; text-align:center; background:linear-gradient(180deg,#ffffff 0%,#f8f4ec 100%);">
                <img src="cid:jobxpresslogo" alt="JobXpress" style="display:block; width:190px; max-width:100%; margin:0 auto 14px;">
                <div style="display:inline-block; padding:6px 12px; border-radius:999px; background:#edf4f3; color:#2f4858; font-size:12px; font-weight:700; letter-spacing:0.04em;">
                    RECUPERACION DE CONTRASEÑA
                </div>
                <h2 style="margin:18px 0 10px; font-size:28px; line-height:1.2; color:#29435a;">
                    Restablece el acceso a tu cuenta
                </h2>
                <p style="margin:0 auto; max-width:470px; font-size:15px; line-height:1.7; color:#5f6f7d;">
                    Recibimos una solicitud para cambiar tu contraseña en JobXpress. Si fuiste tu, usa el siguiente boton para continuar de forma segura.
                </p>
            </div>
            <div style="padding:10px 26px 30px; text-align:center;">
                <a href="{reset_url}"
                   style="display:inline-block; margin-top:12px; background:linear-gradient(135deg,#6f9c95,#29435a); color:#ffffff; padding:14px 26px; text-decoration:none; border-radius:14px; font-size:16px; font-weight:700; box-shadow:0 14px 24px rgba(41,67,90,0.22);">
                    Restablecer contraseña
                </a>
                <p style="margin:22px 0 0; font-size:14px; line-height:1.7; color:#6b7785;">
                    Este enlace estara disponible durante <strong>1 hora</strong>.
                </p>
                <p style="margin:8px 0 0; font-size:14px; line-height:1.7; color:#6b7785;">
                    Si no solicitaste este cambio, puedes ignorar este mensaje sin hacer ninguna accion.
                </p>
            </div>
            <div style="padding:16px 22px 22px; border-top:1px solid rgba(111,156,149,0.16); text-align:center; background:#fcfaf6;">
                <p style="margin:0; font-size:12px; line-height:1.6; color:#8a94a1;">
                    JobXpress · Soporte de cuenta y seguridad
                </p>
            </div>
        </div>
    </div>
    """

    message = EmailMultiAlternatives(
        subject=subject,
        body=text_body,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", settings.EMAIL_HOST_USER),
        to=[email],
    )
    message.attach_alternative(html, "text/html")

    logo_path = settings.BASE_DIR / "static" / "images" / "logo_sidebar_blue.png"
    if logo_path.exists():
        with open(logo_path, "rb") as logo_file:
            logo = MIMEImage(logo_file.read())
        logo.add_header("Content-ID", "<jobxpresslogo>")
        logo.add_header("Content-Disposition", "inline", filename="jobxpress-logo.png")
        message.attach(logo)

    try:
        sent = message.send(fail_silently=False)
    except Exception:
        sent = 0

    if sent < 1:
        return render(
            request,
            "forgot-password.html",
            {"error": "No se pudo enviar el correo de recuperacion. Intenta nuevamente."},
        )

    return redirect("/forgot?success")

def reset_view(request):
    if request.method == "GET":
        token = request.GET.get("token")
        reset_token = PasswordResetToken.objects.filter(token=token).first()
        if not reset_token:
            return redirect("/login?tokenInvalid")
        return render(request, "reset-password.html", {"token": token})

    token = request.POST.get("token")
    password = request.POST.get("password")
    reset_token = PasswordResetToken.objects.filter(token=token).first()
    if not reset_token:
        return redirect("/login?tokenInvalid")

    usuario = reset_token.usuario
    usuario.contrasena = _hash_password(password)
    usuario.save(update_fields=["contrasena"])
    reset_token.delete()

    return redirect("/login?resetOk")
