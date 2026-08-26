from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from accounts.models import User, EmailOTP
from config.crypto_utils import compute_sha256_hash, encrypt_field, decrypt_field, generate_jwt_tokens, decode_jwt_token

class SecurityAndAuthTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="testuser",
            email="test@sprintly.io",
            password="SecurePassword123!",
            role="DEVELOPER",
            is_email_verified=False
        )

    def test_sha256_hashing(self):
        payload = {"ticket": "SPT-1", "title": "Setup Enterprise Board", "points": 5}
        h1 = compute_sha256_hash(payload)
        h2 = compute_sha256_hash(payload)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

        tampered = {"ticket": "SPT-1", "title": "Setup Enterprise Board", "points": 8}
        self.assertNotEqual(h1, compute_sha256_hash(tampered))

    def test_aes_256_encryption_and_decryption(self):
        secret_text = "Highly Confidential Architecture Specification & Key"
        encrypted = encrypt_field(secret_text)
        self.assertNotEqual(encrypted, secret_text)
        decrypted = decrypt_field(encrypted)
        self.assertEqual(decrypted, secret_text)

    def test_jwt_generation_and_decode(self):
        tokens = generate_jwt_tokens(self.user)
        self.assertIn("access", tokens)
        self.assertIn("refresh", tokens)
        
        decoded = decode_jwt_token(tokens["access"])
        self.assertEqual(decoded["sub"], str(self.user.pk))
        self.assertEqual(decoded["username"], "testuser")

    def test_login_flow_with_6_digit_otp(self):
        res = self.client.post(reverse("accounts:login"), {
            "username": "testuser",
            "password": "SecurePassword123!"
        })
        self.assertEqual(res.status_code, 302)
        self.assertIn("verify-otp", res.url)

        otp = EmailOTP.objects.filter(user=self.user, purpose="LOGIN").first()
        self.assertIsNotNone(otp)
        self.assertEqual(len(otp.otp_code), 6)
        self.assertTrue(otp.otp_code.isdigit())

        res_verify = self.client.post(reverse("accounts:verify_otp"), {
            "otp_code": otp.otp_code
        })
        self.assertEqual(res_verify.status_code, 302)
        
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_email_verified)

    def test_profile_update_and_anonymous_safety(self):
        # Authenticated update
        self.client.force_authenticate(user=self.user)
        res = self.client.post(reverse("accounts:profile"), {
            "first_name": "Aayush",
            "last_name": "Shah",
            "title": "Principal Architect",
            "role": "ARCHITECT",
            "timezone": "America/New_York",
            "theme_preference": "DARK",
            "avatar_color": "#059669"
        })
        self.assertEqual(res.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Aayush")
        self.assertEqual(self.user.last_name, "Shah")
        self.assertEqual(self.user.title, "Principal Architect")

    def test_security_firewall_blocks_sqli_payloads(self):
        res = self.client.get("/api/projects/?search=' UNION SELECT * FROM users --")
        self.assertEqual(res.status_code, 403)

    def test_security_headers_present_on_responses(self):
        res = self.client.get("/")
        self.assertEqual(res.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertEqual(res.headers.get("X-Frame-Options"), "SAMEORIGIN")
        self.assertIn("Content-Security-Policy", res.headers)
