import hashlib
import hmac
import json
import base64
import os
from datetime import datetime, timezone, timedelta
from django.conf import settings
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import jwt

# Derive a 256-bit encryption key from Django SECRET_KEY
def _get_encryption_key() -> bytes:
    secret = getattr(settings, 'SECRET_KEY', 'sprintly-default-secret-key-32-chars-min!').encode()
    salt = b'sprintly_aes_salt_v1'
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return kdf.derive(secret)

def compute_sha256_hash(data: dict | str) -> str:
    """
    Computes a deterministic SHA-256 cryptographic hash of data.
    Provides tamper-evident integrity seals for tickets and audit events.
    """
    if isinstance(data, dict):
        serialized = json.dumps(data, sort_keys=True, default=str).encode('utf-8')
    elif isinstance(data, str):
        serialized = data.encode('utf-8')
    else:
        serialized = str(data).encode('utf-8')
    
    return hashlib.sha256(serialized).hexdigest()

def verify_sha256_hash(data: dict | str, expected_hash: str) -> bool:
    """Verifies that data matches the expected SHA-256 hash."""
    actual_hash = compute_sha256_hash(data)
    return hmac.compare_digest(actual_hash, expected_hash)

def encrypt_field(plaintext: str) -> str:
    """
    Encrypts a string using AES-256-GCM authenticated encryption.
    Returns Base64 encoded nonce + ciphertext + tag.
    """
    if not plaintext:
        return ""
    try:
        key = _get_encryption_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)  # 96-bit nonce for AES-GCM
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)
        combined = nonce + ciphertext
        return base64.b64encode(combined).decode('utf-8')
    except Exception as e:
        # Fallback to simple encoded format if crypto error occurs
        return f"ENC_ERR:{str(e)}"

def decrypt_field(encrypted_payload: str) -> str:
    """
    Decrypts an AES-256-GCM encrypted Base64 string.
    """
    if not encrypted_payload or not isinstance(encrypted_payload, str):
        return ""
    if encrypted_payload.startswith("ENC_ERR:"):
        return "[Decryption Error]"
    try:
        raw_bytes = base64.b64decode(encrypted_payload.encode('utf-8'))
        nonce = raw_bytes[:12]
        ciphertext = raw_bytes[12:]
        key = _get_encryption_key()
        aesgcm = AESGCM(key)
        decrypted = aesgcm.decrypt(nonce, ciphertext, None)
        return decrypted.decode('utf-8')
    except Exception:
        # If not encrypted or invalid key, return as-is or error indicator
        return encrypted_payload

def generate_jwt_tokens(user) -> dict:
    """
    Generates Access and Refresh JWT tokens for authenticated users.
    """
    now = datetime.now(timezone.utc)
    jwt_secret = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
    jwt_alg = getattr(settings, 'JWT_ALGORITHM', 'HS256')
    access_exp_seconds = getattr(settings, 'JWT_ACCESS_TOKEN_LIFETIME', 15 * 60)
    refresh_exp_seconds = getattr(settings, 'JWT_REFRESH_TOKEN_LIFETIME', 7 * 24 * 60 * 60)

    import uuid
    access_jti = str(uuid.uuid4())
    refresh_jti = str(uuid.uuid4())

    access_payload = {
        "sub": str(user.pk),
        "username": user.username,
        "email": user.email,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(seconds=access_exp_seconds),
        "jti": access_jti,
    }

    refresh_payload = {
        "sub": str(user.pk),
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(seconds=refresh_exp_seconds),
        "jti": refresh_jti,
    }

    access_token = jwt.encode(access_payload, jwt_secret, algorithm=jwt_alg)
    refresh_token = jwt.encode(refresh_payload, jwt_secret, algorithm=jwt_alg)

    return {
        "access": access_token,
        "refresh": refresh_token,
        "refresh_jti": refresh_jti,
        "refresh_exp": now + timedelta(seconds=refresh_exp_seconds),
    }

def decode_jwt_token(token: str) -> dict:
    """
    Decodes and validates a JWT token.
    """
    jwt_secret = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
    jwt_alg = getattr(settings, 'JWT_ALGORITHM', 'HS256')
    return jwt.decode(token, jwt_secret, algorithms=[jwt_alg])
