from __future__ import annotations

from django.utils.deprecation import MiddlewareMixin
from django.shortcuts import redirect
from django.http import JsonResponse

from .models import Usuario


PUBLIC_PREFIXES = (
    "/index",
    "/login",
    "/registro",
    "/forgot",
    "/reset",
    "/css/",
    "/js/",
    "/images/",
    "/static/",
    "/media/",
    "/api/maps/",
    "/django-admin/",
    "/ping/",
    "/favicon.ico",
)

ROLE_PREFIXES = {
    "/cliente": "ROLE_CLIENTE",
    "/prestador": "ROLE_PRESTADOR",
    "/admin": "ROLE_ADMIN",
}


def _wants_json(request):
    accept = (request.headers.get("Accept") or "").lower()
    requested_with = (request.headers.get("X-Requested-With") or "").lower()
    return "application/json" in accept or requested_with == "xmlhttprequest"


class SessionUserMiddleware(MiddlewareMixin):
    def process_request(self, request):
        usuario_id = request.session.get("usuario_id")
        request.usuario = None
        request.rol = None
        if usuario_id:
            try:
                usuario = Usuario.objects.select_related("rol").get(id_usuario=usuario_id)
                request.usuario = usuario
                request.rol = usuario.rol.rol if usuario.rol else None
            except Usuario.DoesNotExist:
                request.session.pop("usuario_id", None)

        path = request.path or ""
        is_public = path == "/" or any(path == p or path.startswith(p) for p in PUBLIC_PREFIXES)
        if is_public:
            return None

        if not request.usuario:
            if _wants_json(request):
                return JsonResponse({"error": "Sesion expirada"}, status=401)
            return redirect("/login")

        for prefix, role in ROLE_PREFIXES.items():
            if path == prefix or path.startswith(f"{prefix}/"):
                if request.rol != role:
                    return redirect("/")
                break
        return None


class NoCacheMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        path = request.path or ""
        is_public = path == "/" or any(path == p or path.startswith(p) for p in PUBLIC_PREFIXES)

        if not is_public:
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0, no-transform"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"
            response["Referrer-Policy"] = "no-referrer"

        return response
