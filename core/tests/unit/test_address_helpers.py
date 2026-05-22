from django.test import TestCase

from core.view_modules.common import _is_valid_address, _normalize_address


class AddressHelpersTestCase(TestCase):
    def test_address_helpers_validate_expected_format(self):
        valid_address = "  Calle 10 # 20-30  "
        invalid_address = "Direccion sin formato"

        self.assertEqual(_normalize_address(valid_address), "Calle 10 # 20-30")
        self.assertTrue(_is_valid_address(valid_address))
        self.assertFalse(_is_valid_address(invalid_address))
