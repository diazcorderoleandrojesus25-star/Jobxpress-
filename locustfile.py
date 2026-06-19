import os
from urllib.parse import quote_plus

from locust import HttpUser, between, task


BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
ADDRESS = os.getenv("ADDRESS", "Calle 10 # 20-30, Bogota")
ENDPOINT = f"/api/maps/geocode?address={quote_plus(ADDRESS)}"


class GeocodeStressUser(HttpUser):
    host = BASE_URL
    wait_time = between(0.5, 1.0)

    @task
    def geocode_address(self):
        with self.client.get(
            ENDPOINT,
            headers={
                "Accept": "application/json",
                "X-Requested-With": "XMLHttpRequest",
            },
            name="/api/maps/geocode",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"status {response.status_code}")
                return

            try:
                payload = response.json()
            except ValueError:
                response.failure("invalid json")
                return

            if not isinstance(payload.get("lat"), (int, float)):
                response.failure("missing lat")
                return

            if not isinstance(payload.get("lng"), (int, float)):
                response.failure("missing lng")
                return

            response.success()
