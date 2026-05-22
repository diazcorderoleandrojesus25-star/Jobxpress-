from .common import *
from ..integrations.google_maps import (
    GoogleMapsConfigError,
    GoogleMapsRequestError,
    geocode_address,
)


def api_maps_geocode(request):
    address = _normalize_address(request.GET.get("address"))
    if not address:
        return _json_error("direccion requerida")
    if not _is_valid_address(address):
        return _json_error("direccion invalida")

    try:
        result = geocode_address(address)
    except GoogleMapsConfigError:
        return _json_error("Google Maps no esta configurado", status=500)
    except GoogleMapsRequestError:
        return _json_error("No se pudo consultar Google Maps", status=502)

    if not result:
        return _json_error("La direccion ingresada no pudo ubicarse en el mapa.", status=422)

    return JsonResponse(result)
