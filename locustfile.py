import os

from locust import HttpUser, between, task


BASE_URL = os.getenv("BASE_URL", "https://jobxpress.up.railway.app").rstrip("/")
LOCUST_EMAIL = os.getenv("LOCUST_EMAIL", "").strip()
LOCUST_PASSWORD = os.getenv("LOCUST_PASSWORD", "").strip()


class LoginContratacionesUser(HttpUser):
    host = BASE_URL
    wait_time = between(0.5, 1.5)

    def on_start(self):
        self.authenticated = False

    @task
    def login_page(self):
        self.client.get("/login", name="/login")

    @task
    def login_post(self):
        if not LOCUST_EMAIL or not LOCUST_PASSWORD:
            return

        with self.client.post(
            "/login",
            data={"username": LOCUST_EMAIL, "password": LOCUST_PASSWORD},
            name="POST /login",
            allow_redirects=False,
            catch_response=True,
        ) as response:
            if response.status_code in (302, 303):
                self.authenticated = True
                response.success()
                return

            response.failure(f"status {response.status_code}")

    @task
    def contrataciones_list(self):
        headers = {"Accept": "application/json"}
        with self.client.get(
            "/contrataciones",
            name="/contrataciones",
            headers=headers,
            catch_response=True,
        ) as response:
            if response.status_code == 401:
                response.success()
                return

            if response.status_code != 200:
                response.failure(f"status {response.status_code}")
                return

            try:
                data = response.json()
            except Exception:
                response.failure("invalid json")
                return

            if not isinstance(data, list):
                response.failure("unexpected payload")
                return

            response.success()
