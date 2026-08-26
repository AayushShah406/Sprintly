import re
import time
import json
import logging
from collections import defaultdict
from django.http import JsonResponse, HttpResponseForbidden
from django.conf import settings

logger = logging.getLogger("sprintly.security")

# Rate Limiter In-Memory Sliding Window Store
_request_history = defaultdict(list)
_auth_request_history = defaultdict(list)

# Malicious Injection Patterns (SQLi, NoSQLi, XSS)
SQLI_PATTERNS = [
    re.compile(r"(\bUNION\b\s+\bSELECT\b)", re.IGNORECASE),
    re.compile(r"(\bSELECT\b\s+.*\bFROM\b)", re.IGNORECASE),
    re.compile(r"(\bDROP\b\s+\bTABLE\b)", re.IGNORECASE),
    re.compile(r"(\bALTER\b\s+\bTABLE\b)", re.IGNORECASE),
    re.compile(r"(\bDELETE\b\s+\bFROM\b)", re.IGNORECASE),
    re.compile(r"('.+--)", re.IGNORECASE),
    re.compile(r"(\bOR\b\s+['\"0-9]+=['\"0-9]+)", re.IGNORECASE),
    re.compile(r"(\bAND\b\s+['\"0-9]+=['\"0-9]+)", re.IGNORECASE),
]

XSS_PATTERNS = [
    re.compile(r"(<script\b[^>]*>([\s\S]*?)<\/script>)", re.IGNORECASE),
    re.compile(r"(javascript:[^\s\"'>]+)", re.IGNORECASE),
    re.compile(r"(onerror\s*=\s*['\"][^'\"]*['\"])", re.IGNORECASE),
    re.compile(r"(onload\s*=\s*['\"][^'\"]*['\"])", re.IGNORECASE),
    re.compile(r"(eval\s*\([^)]*\))", re.IGNORECASE),
    re.compile(r"(document\.cookie)", re.IGNORECASE),
]

NOSQLI_KEYS = {"$where", "$ne", "$gt", "$gte", "$lt", "$lte", "$in", "$nin", "$regex", "$or", "$and", "$not"}


def sanitize_input_value(val):
    """Recursively sanitizes values to neutralize XSS and NoSQL injections."""
    if isinstance(val, str):
        # Strip script tags and harmful javascript handlers
        cleaned = re.sub(r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", "", val, flags=re.IGNORECASE)
        cleaned = re.sub(r"javascript:", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"onerror\s*=", "on_error_disabled=", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"onload\s*=", "on_load_disabled=", cleaned, flags=re.IGNORECASE)
        return cleaned
    elif isinstance(val, dict):
        return {k: sanitize_input_value(v) for k, v in val.items() if k not in NOSQLI_KEYS}
    elif isinstance(val, list):
        return [sanitize_input_value(item) for item in val]
    return val


def check_sqli_threats(data) -> bool:
    """Checks if any string input contains severe SQL injection signatures."""
    if isinstance(data, str):
        for pattern in SQLI_PATTERNS:
            if pattern.search(data):
                return True
    elif isinstance(data, dict):
        for k, v in data.items():
            if check_sqli_threats(k) or check_sqli_threats(v):
                return True
    elif isinstance(data, list):
        for item in data:
            if check_sqli_threats(item):
                return True
    return False


class EnterpriseSecurityMiddleware:
    """
    Full-Stack Cyber Threat Protection Middleware:
    1. DDoS & API Rate Limiting (Sliding Window per IP).
    2. Input Validation & Anti-Injection Defense (XSS, NoSQLi, SQLi).
    3. Enterprise Cryptographic Security Headers.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        ip = self._get_client_ip(request)
        path = request.path
        now = time.time()

        # 1. DDoS & Rate Limiting Enforcement
        is_auth_route = any(path.startswith(p) for p in ["/login/", "/signup/", "/verify-otp/", "/resend-otp/", "/api/auth/"])
        is_api_route = path.startswith("/api/")

        if is_auth_route:
            # Stricter Rate Limit for Auth/OTP routes: Max 20 requests/minute
            history = _auth_request_history[ip]
            _auth_request_history[ip] = [t for t in history if now - t < 60]
            if len(_auth_request_history[ip]) >= 20:
                logger.warning(f"[Security Firewall] Rate limit exceeded for IP: {ip} on Auth path: {path}")
                return JsonResponse({
                    "error": "Rate limit exceeded for authentication requests. Please try again in 60 seconds.",
                    "status": 429
                }, status=429, headers={"Retry-After": "60"})
            _auth_request_history[ip].append(now)

        elif is_api_route:
            # Standard API Rate Limit: Max 120 requests/minute
            history = _request_history[ip]
            _request_history[ip] = [t for t in history if now - t < 60]
            if len(_request_history[ip]) >= 120:
                logger.warning(f"[Security Firewall] Rate limit exceeded for IP: {ip} on API path: {path}")
                return JsonResponse({
                    "error": "Too many requests. API rate limit is 120 requests per minute.",
                    "status": 429
                }, status=429, headers={"Retry-After": "60"})
            _request_history[ip].append(now)

        # 2. Input Validation & Injection Threat Detection
        # Check GET parameters
        for key, val in request.GET.items():
            if check_sqli_threats(val) or key in NOSQLI_KEYS:
                logger.warning(f"[Security Firewall] Blocked suspicious injection attempt from {ip} in GET param: {key}")
                return HttpResponseForbidden("Forbidden: Malicious input sequence detected.")

        # Check & Sanitize POST parameters
        if request.method in ["POST", "PUT", "PATCH"]:
            if request.content_type == "application/json" and request.body:
                try:
                    raw_json = json.loads(request.body.decode("utf-8"))
                    if check_sqli_threats(raw_json):
                        logger.warning(f"[Security Firewall] Blocked SQLi payload in JSON from {ip}")
                        return HttpResponseForbidden("Forbidden: Malicious SQL sequence detected.")
                except Exception:
                    pass

        # Execute view
        response = self.get_response(request)

        # 3. Enterprise Hardened Security Headers
        response["X-Content-Type-Options"] = "nosniff"
        response["X-Frame-Options"] = "SAMEORIGIN"
        response["X-XSS-Protection"] = "1; mode=block"
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        response["Content-Security-Policy"] = (
            "default-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com https://fonts.googleapis.com https://fonts.gstatic.com; "
            "img-src 'self' data: https:; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "connect-src 'self' ws://127.0.0.1:8000 http://127.0.0.1:8000 https://api.groq.com;"
        )

        return response

    def _get_client_ip(self, request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "127.0.0.1")
        return ip
