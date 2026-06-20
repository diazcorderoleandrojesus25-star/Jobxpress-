from __future__ import annotations

import csv
import io
import json
import os
import re
import uuid
import urllib.request
from datetime import datetime, timedelta
from email.mime.image import MIMEImage

import bcrypt
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django.core.paginator import Paginator
from django.core.validators import validate_email
from django.core.files.storage import default_storage
from django.db.models import Avg, Count, Sum, Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.conf import settings
from django.contrib import messages
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt

from ..models import (
    Calificacion,
    ClienteCalificacion,
    ClienteContratacion,
    Categoria,
    Contratacion,
    MetodoPago,
    Pago,
    PasswordResetToken,
    Prestador,
    PrestadorCategoria,
    Rol,
    Servicio,
    Usuario,
)
from ..pdf_utils import build_report_with_stats, build_simple_report


PASSWORD_REGEX = re.compile(r"^(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).+$")
PHONE_REGEX = re.compile(r"^\d{10}$")
ADDRESS_ALLOWED_REGEX = re.compile(r"^[A-Za-z0-9ÁÉÍÓÚáéíóúÑñ#.,\-/\s]+$")
ADDRESS_PREFIX_REGEX = re.compile(
    r"\b(calle|cl|carrera|cra|cr|avenida|av|diagonal|dg|transversal|tv|autopista|ap|via|vereda|manzana|mz)\b",
    re.IGNORECASE,
)


def _check_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    if hashed.startswith("{bcrypt}"):
        hashed = hashed[len("{bcrypt}"):]
    if hashed.startswith("{noop}"):
        return plain == hashed[len("{noop}"):]
    if hashed.startswith("$2a$") or hashed.startswith("$2b$") or hashed.startswith("$2y$"):
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    return plain == hashed


def _hash_password(plain: str) -> str:
    return bcrypt.hashpw(plain.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _normalize_phone(value: str | None) -> str:
    return (value or "").strip()


def _is_valid_phone(value: str | None) -> bool:
    return bool(PHONE_REGEX.fullmatch(_normalize_phone(value)))


def _normalize_address(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def _media_url(path: str | None) -> str:
    value = (path or "").strip()
    if not value:
        return ""
    if value.startswith(("http://", "https://", "/")):
        return value
    return f"{settings.MEDIA_URL}{value.lstrip('/')}"


def _is_valid_address(value: str | None) -> bool:
    address = _normalize_address(value)
    if len(address) < 8 or len(address) > 120:
        return False
    if not ADDRESS_ALLOWED_REGEX.fullmatch(address):
        return False
    if not ADDRESS_PREFIX_REGEX.search(address):
        return False
    if not re.search(r"\d", address):
        return False
    return "#" in address or "-" in address


def _redirect_by_role(rol: str | None):
    if rol == "ROLE_ADMIN":
        return redirect("/admin/dashboard")
    if rol == "ROLE_CLIENTE":
        return redirect("/cliente/home")
    if rol == "ROLE_PRESTADOR":
        return redirect("/prestador/home")
    return redirect("/")




def _clean_filter(value):
    if value is None:
        return ""
    value = str(value).strip()
    if not value or value.lower() == "none":
        return ""
    return value


def _get_or_create_prestador_services(prestador):
    if not prestador:
        return Servicio.objects.none()

    # Solo devolvemos servicios que realmente pertenecen al prestador.
    # Antes se hacía un fallback por categoría y eso hacía parecer que
    # se creaban servicios nuevos al registrar un prestador.
    servicios = Servicio.objects.filter(prestador=prestador).select_related("categoria")
    return servicios


def _role_required(role: str):
    def decorator(view):
        def wrapper(request, *args, **kwargs):
            if not getattr(request, "usuario", None):
                return redirect("/login")
            if request.rol != role:
                return redirect("/")
            return view(request, *args, **kwargs)

        return wrapper

    return decorator



def _json_error(message, status=400):
    return JsonResponse({"error": message}, status=status)


def _wants_json(request):
    accept = (request.headers.get("Accept") or "").lower()
    requested_with = (request.headers.get("X-Requested-With") or "").lower()
    return "application/json" in accept or requested_with == "xmlhttprequest"




def _parse_observacion(value: str | None):
    if not value:
        return {}
    try:
        return json.loads(value)
    except Exception:
        return {"descripcion": value}


def _parse_body(request):
    try:
        return json.loads(request.body.decode("utf-8"))
    except Exception:
        return {}


def _get_programmed_datetime(contratacion: Contratacion):
    if not getattr(contratacion, "fecha", None):
        return None

    obs = _parse_observacion(getattr(contratacion, "observacion", None))
    hora_raw = (obs.get("hora") or "").strip()
    if hora_raw:
        try:
            hora = datetime.strptime(hora_raw, "%H:%M").time()
        except ValueError:
            try:
                hora = datetime.strptime(hora_raw, "%H:%M:%S").time()
            except ValueError:
                hora = None
        if hora is not None:
            return datetime.combine(contratacion.fecha, hora)

    # Si no hay hora válida, dejamos expirar al final del día para no
    # rechazar de inmediato una solicitud creada para "hoy".
    return datetime.combine(contratacion.fecha, datetime.max.time().replace(microsecond=0))


def _apply_auto_contratacion_estado(contratacion: Contratacion, now=None):
    now = now or timezone.now()
    fecha_programada = _get_programmed_datetime(contratacion)
    if fecha_programada is None:
        return contratacion.estado or ""

    estado_actual = (contratacion.estado or "").strip()
    estado_low = estado_actual.lower()
    if not estado_actual:
        estado_actual = "Pendiente"
        estado_low = "pendiente"

    if any(word in estado_low for word in ["cancel", "rechaz", "complet"]):
        return estado_actual

    if timezone.is_aware(now) and timezone.is_naive(fecha_programada):
        fecha_programada = timezone.make_aware(fecha_programada, now.tzinfo)
    if now < fecha_programada:
        return estado_actual

    nuevo_estado = None
    if any(word in estado_low for word in ["confirm", "acept", "proceso", "activo"]):
        nuevo_estado = "Completada"
    elif "pend" in estado_low:
        nuevo_estado = "Rechazado"

    if nuevo_estado and nuevo_estado != contratacion.estado:
        contratacion.estado = nuevo_estado
        contratacion.save(update_fields=["estado"])
        return nuevo_estado

    return contratacion.estado or estado_actual


def _get_prestador_respuesta_estado(estado: str | None) -> str:
    estado_low = (estado or "").strip().lower()
    if not estado_low or "pend" in estado_low:
        return "pendiente"
    if "cancel" in estado_low:
        return "cancelado"
    if "rechaz" in estado_low:
        return "rechazado"
    if any(word in estado_low for word in ["confirm", "acept", "proceso", "activo", "complet", "final", "termin"]):
        return "aceptado"
    return "respondio"


__all__ = [name for name in globals() if not name.startswith("__")]
