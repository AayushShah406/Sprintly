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


from django.core.files.uploadedfile import SimpleUploadedFile

class ProfileAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username="alexdev",
            email="alex@sprintly.io",
            password="SecurePassword123!",
            first_name="Alex",
            last_name="Rivers",
            role="DEVELOPER"
        )
        self.other_user = User.objects.create_user(
            username="janesmith",
            email="jane@sprintly.io",
            password="SecurePassword123!",
            first_name="Jane",
            last_name="Smith",
            role="MANAGER"
        )

    def test_get_profile_authenticated(self):
        self.client.force_authenticate(user=self.user)
        res = self.client.get(reverse("accounts:api_profile"))
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["username"], "alexdev")
        self.assertEqual(data["email"], "alex@sprintly.io")
        self.assertEqual(data["first_name"], "Alex")
        self.assertEqual(data["last_name"], "Rivers")
        self.assertIn("job_title", data)
        self.assertIn("location", data)
        self.assertIn("bio", data)
        self.assertIn("role", data)
        self.assertIn("department", data)
        self.assertIn("joined_date", data)
        self.assertNotIn("password", data)
        self.assertNotIn("password_hash", data)

    def test_get_profile_unauthenticated_returns_401(self):
        res = self.client.get(reverse("accounts:api_profile"))
        self.assertEqual(res.status_code, 401)

    def test_put_profile_updates_and_persists_to_database(self):
        self.client.force_authenticate(user=self.user)
        payload = {
            "first_name": "Alexander",
            "last_name": "Rivers-Stone",
            "job_title": "Principal Agile Architect",
            "location": "San Francisco, CA",
            "bio": "Building next-generation agile tooling and scalable cloud architectures."
        }
        res = self.client.put(reverse("accounts:api_profile"), payload, format="json")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data["first_name"], "Alexander")
        self.assertEqual(data["job_title"], "Principal Agile Architect")
        self.assertEqual(data["location"], "San Francisco, CA")

        # Database verification
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Alexander")
        self.assertEqual(self.user.last_name, "Rivers-Stone")
        profile = self.user.profile
        self.assertEqual(profile.job_title, "Principal Agile Architect")
        self.assertEqual(profile.location, "San Francisco, CA")
        self.assertEqual(profile.bio, "Building next-generation agile tooling and scalable cloud architectures.")

    def test_put_profile_email_uniqueness_enforced(self):
        self.client.force_authenticate(user=self.user)
        # Attempt to claim Jane's email
        res = self.client.put(reverse("accounts:api_profile"), {
            "email": "jane@sprintly.io"
        }, format="json")
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertIn("error", data)
        self.assertIn("already in use", data["error"].lower())

    def test_put_profile_username_uniqueness_enforced(self):
        self.client.force_authenticate(user=self.user)
        # Attempt to claim Jane's username
        res = self.client.put(reverse("accounts:api_profile"), {
            "username": "janesmith"
        }, format="json")
        self.assertEqual(res.status_code, 400)
        data = res.json()
        self.assertIn("error", data)
        self.assertIn("already taken", data["error"].lower())

    def test_put_profile_readonly_fields_immutable(self):
        self.client.force_authenticate(user=self.user)
        original_joined = self.user.profile.created_at
        # Attempt to modify role and department
        res = self.client.put(reverse("accounts:api_profile"), {
            "first_name": "Alex",
            "role": "ADMIN",
            "department": "Executive Leadership",
            "joined_date": "2010-01-01"
        }, format="json")
        self.assertEqual(res.status_code, 200)

        self.user.refresh_from_db()
        self.assertEqual(self.user.role, "DEVELOPER")
        self.assertEqual(self.user.profile.department, "Engineering")

    def test_put_profile_picture_upload(self):
        self.client.force_authenticate(user=self.user)
        # Create a small valid 1x1 GIF
        gif_bytes = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\xff\xff\xff\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'
        avatar = SimpleUploadedFile("test_avatar.gif", gif_bytes, content_type="image/gif")

        res = self.client.put(reverse("accounts:api_profile"), {
            "first_name": "Alex",
            "profile_picture": avatar
        }, format="multipart")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIsNotNone(data["profile_picture"])

        self.user.profile.refresh_from_db()
        self.assertTrue(bool(self.user.profile.profile_picture))

    def test_jwt_bearer_authentication_for_profile_api(self):
        tokens = generate_jwt_tokens(self.user)
        client = APIClient()
        # Call API using JWT Bearer token in header without session login
        res = client.get(
            reverse("accounts:api_profile"),
            HTTP_AUTHORIZATION=f"Bearer {tokens['access']}"
        )
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.json()["username"], "alexdev")

