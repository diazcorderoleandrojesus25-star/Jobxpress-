from __future__ import annotations

import json
import urllib.parse
import urllib.request

from django.conf import settings


GEOCODING_ENDPOINT = "https://maps.googleapis.com/maps/api/geocode/json"
ALLOWED_LOCATION_TYPES = {"ROOFTOP", "RANGE_INTERPOLATED"}


class GoogleMapsConfigError(Exception):
    pass


class GoogleMapsRequestError(Exception):
    pass


def _has_component(result: dict, component_type: str) -> bool:
    components = result.get("address_components") or []
    return any(component_type in (component.get("types") or []) for component in components)


def _is_specific_address(result: dict) -> bool:
    if not result or result.get("partial_match"):
        return False

    geometry = result.get("geometry") or {}
    if (geometry.get("location_type") or "") not in ALLOWED_LOCATION_TYPES:
        return False

    types = result.get("types") or []
    if "route" in types and not _has_component(result, "street_number"):
        return False

    return _has_component(result, "route") and _has_component(result, "street_number")


def geocode_address(address: str, country_code: str = "CO", timeout: int = 10) -> dict | None:
    api_key = (getattr(settings, "GOOGLE_MAPS_API_KEY", "") or "").strip()
    if not api_key:
        raise GoogleMapsConfigError("GOOGLE_MAPS_API_KEY no configurada")

    params = {
        "address": address,
        "components": f"country:{country_code}",
        "key": api_key,
    }
    url = f"{GEOCODING_ENDPOINT}?{urllib.parse.urlencode(params)}"
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "JobXpress/1.0",
        },
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        raise GoogleMapsRequestError("No se pudo consultar Google Maps") from exc

    if payload.get("status") != "OK":
        return None

    results = payload.get("results") or []
    if not results:
        return None

    top = results[0]
    if not _is_specific_address(top):
        return None

    location = ((top.get("geometry") or {}).get("location") or {})
    lat = location.get("lat")
    lng = location.get("lng")
    if lat is None or lng is None:
        return None

    return {
        "address": top.get("formatted_address") or address,
        "lat": float(lat),
        "lng": float(lng),
        "place_id": top.get("place_id") or "",
    }
