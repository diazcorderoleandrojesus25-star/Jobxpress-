from django.test import TestCase, override_settings

from core.view_modules.common import _media_url


class MediaHelpersTestCase(TestCase):
    @override_settings(MEDIA_URL="/media/")
    def test_media_url_builds_url_for_relative_path(self):
        self.assertEqual(_media_url("perfiles/prestador_7.jpg"), "/media/perfiles/prestador_7.jpg")

    @override_settings(MEDIA_URL="/media/")
    def test_media_url_keeps_absolute_or_empty_values(self):
        self.assertEqual(_media_url("/media/perfiles/prestador_7.jpg"), "/media/perfiles/prestador_7.jpg")
        self.assertEqual(_media_url(""), "")
