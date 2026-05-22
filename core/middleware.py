from __future__ import annotations

from django.utils.deprecation import MiddlewareMixin

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
)


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
