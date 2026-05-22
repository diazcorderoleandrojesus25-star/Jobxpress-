from django.test import TestCase


class HomeIntegrationTestCase(TestCase):
    def test_home_renders_public_landing_page_for_anonymous_user(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "index.html")
