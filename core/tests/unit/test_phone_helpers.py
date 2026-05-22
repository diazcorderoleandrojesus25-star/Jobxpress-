from django.test import TestCase

from core.view_modules.common import _is_valid_phone, _normalize_phone


class PhoneHelpersTestCase(TestCase):
    def test_phone_helpers_accept_only_ten_digits(self):
        self.assertEqual(_normalize_phone(" 3001234567 "), "3001234567")
        self.assertTrue(_is_valid_phone("3001234567"))
        self.assertFalse(_is_valid_phone("300123456"))
        self.assertFalse(_is_valid_phone("300-123-4567"))
