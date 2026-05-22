import json
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings

from core.integrations.google_maps.geocoding import geocode_address


class GoogleMapsRestTestCase(TestCase):
    @override_settings(GOOGLE_MAPS_API_KEY="test-key")
    def test_geocode_address_returns_coordinates_for_specific_address(self):
        payload = {
            "status": "OK",
            "results": [
                {
                    "formatted_address": "Calle 10 # 20-30, Bogota, Colombia",
                    "place_id": "abc123",
                    "types": ["street_address"],
                    "address_components": [
                        {"types": ["route"]},
                        {"types": ["street_number"]},
                    ],
                    "geometry": {
                        "location_type": "ROOFTOP",
                        "location": {"lat": 4.65, "lng": -74.1},
                    },
                }
            ],
        }

        response = Mock()
        response.read.return_value = json.dumps(payload).encode("utf-8")
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=None)

        with patch("urllib.request.urlopen", return_value=response):
            result = geocode_address("Calle 10 # 20-30")

        self.assertEqual(
            result,
            {
                "address": "Calle 10 # 20-30, Bogota, Colombia",
                "lat": 4.65,
                "lng": -74.1,
                "place_id": "abc123",
            },
        )

    @override_settings(GOOGLE_MAPS_API_KEY="test-key")
    def test_api_maps_geocode_returns_422_for_imprecise_google_result(self):
        payload = {
            "status": "OK",
            "results": [
                {
                    "formatted_address": "Bogota, Colombia",
                    "types": ["route"],
                    "address_components": [{"types": ["route"]}],
                    "geometry": {
                        "location_type": "GEOMETRIC_CENTER",
                        "location": {"lat": 4.6, "lng": -74.0},
                    },
                }
            ],
        }

        response = Mock()
        response.read.return_value = json.dumps(payload).encode("utf-8")
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=None)

        with patch("urllib.request.urlopen", return_value=response):
            result = self.client.get(
                "/api/maps/geocode",
                {"address": "Calle 10 # 20-30"},
                HTTP_X_REQUESTED_WITH="XMLHttpRequest",
            )

        self.assertEqual(result.status_code, 422)
        self.assertJSONEqual(
            result.content,
            {"error": "La direccion ingresada no pudo ubicarse en el mapa."},
        )
