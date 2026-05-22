from django.test import TestCase

from core.view_modules.common import _check_password, _hash_password


class PasswordHelpersTestCase(TestCase):
    # Verifica que el hash generado no sea texto plano y que pueda validarse.
    def test_hash_password_generates_bcrypt_hash_and_validates(self):
        plain_password = "Segura123!"
        hashed_password = _hash_password(plain_password)

        self.assertNotEqual(hashed_password, plain_password)
        self.assertTrue(hashed_password.startswith("$2"))
        self.assertTrue(_check_password(plain_password, hashed_password))
        self.assertFalse(_check_password("Otra123!", hashed_password))
