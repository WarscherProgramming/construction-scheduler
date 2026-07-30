import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.api.routes_auth import login_rate_limiter
from app.core.config import (
    AUTH_LOGIN_RATE_LIMIT,
    CSRF_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
)
from app.main import app
from tests.test_api import ApiTestCase


ORIGIN = "http://localhost:5173"
BACKEND_ROOT = Path(__file__).resolve().parents[1]


def production_environment(**overrides) -> dict[str, str]:
    environment = os.environ.copy()
    environment.update(
        {
            "APP_ENV": "production",
            "APP_DEBUG": "false",
            "DATABASE_URL": "sqlite:///production-config-test.db",
            "SECRET_KEY": "s" * 48,
            "REFRESH_TOKEN_SECRET": "r" * 48,
            "ALLOWED_ORIGINS": "https://frontend.example",
            "COOKIE_SECURE": "true",
            "COOKIE_SAMESITE": "none",
        }
    )
    environment.update(overrides)
    return environment


def run_config_import(**overrides) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", "import app.core.config"],
        cwd=BACKEND_ROOT,
        env=production_environment(**overrides),
        capture_output=True,
        text=True,
        timeout=15,
        check=False,
    )


class ProductionConfigurationTests(unittest.TestCase):
    def test_valid_production_configuration_imports(self):
        result = run_config_import()
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_production_rejects_unsafe_configuration(self):
        cases = [
            (
                {"APP_ENV": "staging"},
                "APP_ENV must be development, test, or production",
            ),
            (
                {"APP_DEBUG": "true"},
                "APP_DEBUG must be false in production",
            ),
            (
                {"ALLOWED_ORIGINS": ""},
                "ALLOWED_ORIGINS is required in production",
            ),
            (
                {"ALLOWED_ORIGINS": "*"},
                "cannot contain wildcard or null origins",
            ),
            (
                {"ALLOWED_ORIGINS": "https://frontend.example.attacker/path"},
                "must contain absolute HTTP(S) origins",
            ),
            (
                {"ALLOWED_ORIGINS": "http://frontend.example"},
                "Production ALLOWED_ORIGINS must use HTTPS",
            ),
            (
                {"COOKIE_SECURE": "false", "COOKIE_SAMESITE": "lax"},
                "COOKIE_SECURE must be true in production",
            ),
            (
                {"COOKIE_SECURE": "false", "COOKIE_SAMESITE": "none"},
                "COOKIE_SAMESITE=none requires COOKIE_SECURE=true",
            ),
            (
                {"ACCESS_TOKEN_EXPIRE_MINUTES": "61"},
                "ACCESS_TOKEN_EXPIRE_MINUTES must be at most 60",
            ),
            (
                {"REFRESH_TOKEN_EXPIRE_DAYS": "91"},
                "REFRESH_TOKEN_EXPIRE_DAYS must be at most 90",
            ),
            (
                {"AUTH_LOGIN_RATE_LIMIT": "101"},
                "AUTH_LOGIN_RATE_LIMIT must be at most 100",
            ),
            (
                {"MAX_REQUEST_BODY_BYTES": "134217729"},
                "MAX_REQUEST_BODY_BYTES must be at most 134217728",
            ),
        ]

        for variables, message in cases:
            with self.subTest(variables=tuple(variables)):
                result = run_config_import(**variables)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(message, result.stderr)

    def test_production_cookie_attributes_are_cross_site_compatible(self):
        script = """
from starlette.responses import Response
from app.api.routes_auth import _set_csrf_cookie, _set_refresh_cookie
from app.core.config import CSRF_COOKIE_NAME, REFRESH_COOKIE_NAME

response = Response()
_set_refresh_cookie(response, "refresh-value")
_set_csrf_cookie(response, "csrf-value")
headers = [
    value.decode("latin-1")
    for name, value in response.raw_headers
    if name.lower() == b"set-cookie"
]
refresh = next(value for value in headers if value.startswith(REFRESH_COOKIE_NAME))
csrf = next(value for value in headers if value.startswith(CSRF_COOKIE_NAME))
assert "HttpOnly" in refresh
assert "HttpOnly" not in csrf
assert "Secure" in refresh and "Secure" in csrf
assert "SameSite=none" in refresh and "SameSite=none" in csrf
assert "Path=/auth" in refresh and "Path=/auth" in csrf
assert "Max-Age=" in refresh and "Max-Age=" in csrf
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            cwd=BACKEND_ROOT,
            env=production_environment(),
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_deployment_contract_declares_required_production_values(self):
        render_config = (BACKEND_ROOT / "render.yaml").read_text()
        for expected in (
            "key: APP_ENV",
            "value: production",
            "key: APP_DEBUG",
            "key: DATABASE_URL",
            "key: SECRET_KEY",
            "key: REFRESH_TOKEN_SECRET",
            "key: COOKIE_SECURE",
            "key: COOKIE_SAMESITE",
        ):
            with self.subTest(expected=expected):
                self.assertIn(expected, render_config)

        frontend_example = (
            BACKEND_ROOT.parent / "frontend" / ".env.example"
        ).read_text()
        self.assertIn("VITE_API_URL=", frontend_example)
        self.assertIn("VITE_AUTH_REQUEST_TIMEOUT_MS=", frontend_example)

        vercel_config = json.loads(
            (BACKEND_ROOT.parent / "frontend" / "vercel.json").read_text()
        )
        headers = {
            item["key"]: item["value"]
            for rule in vercel_config["headers"]
            for item in rule["headers"]
        }
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(headers["X-Frame-Options"], "DENY")
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")
        self.assertIn("camera=()", headers["Permissions-Policy"])


class ProductionRequestSecurityTests(ApiTestCase):
    def login(self, email="production-check@example.com"):
        self.client.post(
            "/auth/register",
            json={"email": email, "password": "Secret123!"},
        )
        return self.client.post(
            "/auth/login",
            data={"username": email, "password": "Secret123!"},
        )

    def test_health_response_is_public_minimal_and_not_cacheable(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "online"})
        self.assertEqual(response.headers["Cache-Control"], "no-store")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")

    def test_cors_origins_are_matched_exactly(self):
        allowed = self.client.options(
            "/auth/refresh",
            headers={
                "Origin": ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": (
                    "Authorization, X-CSRF-Token"
                ),
            },
        )
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(
            allowed.headers["Access-Control-Allow-Origin"],
            ORIGIN,
        )
        self.assertEqual(
            allowed.headers["Access-Control-Allow-Credentials"],
            "true",
        )
        self.assertIn("Origin", allowed.headers["Vary"])

        denied_origins = (
            "null",
            f"{ORIGIN}.attacker.example",
            "http://localhost:51730",
            "https://localhost:5173",
            "http://localhost",
        )
        for origin in denied_origins:
            with self.subTest(origin=origin):
                denied = self.client.options(
                    "/auth/refresh",
                    headers={
                        "Origin": origin,
                        "Access-Control-Request-Method": "POST",
                    },
                )
                self.assertNotEqual(denied.status_code, 200)
                self.assertNotIn(
                    "Access-Control-Allow-Origin",
                    denied.headers,
                )

    def test_csrf_rejects_missing_malformed_and_untrusted_origins(self):
        login = self.login()
        csrf = login.json()["csrf_token"]
        cases = [
            {},
            {"Origin": ORIGIN},
            {"Origin": ORIGIN, "X-CSRF-Token": ""},
            {"Origin": ORIGIN, "X-CSRF-Token": "malformed"},
            {
                "Origin": f"{ORIGIN}.attacker.example",
                "X-CSRF-Token": csrf,
            },
        ]
        for headers in cases:
            with self.subTest(headers=tuple(headers)):
                response = self.client.post(
                    "/auth/refresh",
                    headers=headers,
                )
                self.assertEqual(response.status_code, 403)
                self.assertEqual(
                    response.json(),
                    {"detail": "Request could not be verified"},
                )

        valid = self.client.post(
            "/auth/refresh",
            headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
        )
        self.assertEqual(valid.status_code, 200)

    def test_spoofed_forwarded_headers_do_not_bypass_rate_limit(self):
        email = "forwarded@example.com"
        self.client.post(
            "/auth/register",
            json={"email": email, "password": "Secret123!"},
        )

        for index in range(AUTH_LOGIN_RATE_LIMIT):
            response = self.client.post(
                "/auth/login",
                data={"username": email, "password": "WrongPassword!"},
                headers={"X-Forwarded-For": f"198.51.100.{index + 1}"},
            )
            self.assertEqual(response.status_code, 401)

        limited = self.client.post(
            "/auth/login",
            data={"username": email, "password": "WrongPassword!"},
            headers={"X-Forwarded-For": "203.0.113.200"},
        )
        self.assertEqual(limited.status_code, 429)
        self.assertIn("Retry-After", limited.headers)

    def test_authentication_logs_do_not_include_credentials_or_tokens(self):
        password = "UniqueLogPassword123!"
        email = "log-review@example.com"
        self.client.post(
            "/auth/register",
            json={"email": email, "password": password},
        )

        with patch("app.api.routes_auth.logger") as logger:
            login = self.client.post(
                "/auth/login",
                data={"username": email, "password": password},
            )
            self.assertEqual(login.status_code, 200)
            csrf = login.json()["csrf_token"]
            refreshed = self.client.post(
                "/auth/refresh",
                headers={"Origin": ORIGIN, "X-CSRF-Token": csrf},
            )
            self.assertEqual(refreshed.status_code, 200)

        log_output = repr(logger.method_calls)
        self.assertIn("Authentication login succeeded", log_output)
        self.assertIn("Authentication refresh succeeded", log_output)
        sensitive_values = (
            password,
            login.json()["access_token"],
            login.json()["csrf_token"],
            login.cookies.get(REFRESH_COOKIE_NAME),
            refreshed.json()["access_token"],
            refreshed.json()["csrf_token"],
            refreshed.cookies.get(CSRF_COOKIE_NAME),
        )
        for value in sensitive_values:
            with self.subTest(value_type=type(value).__name__):
                self.assertNotIn(value, log_output)

    def test_public_documentation_is_intentionally_available(self):
        self.assertEqual(self.client.get("/openapi.json").status_code, 200)
        self.assertEqual(self.client.get("/docs").status_code, 200)

    def test_cleanup_failure_does_not_break_login_or_rotation(self):
        self.client.post(
            "/auth/register",
            json={
                "email": "cleanup-resilience@example.com",
                "password": "Secret123!",
            },
        )
        with patch(
            "app.services.auth_session.cleanup_refresh_sessions",
            side_effect=SQLAlchemyError("cleanup unavailable"),
        ):
            login = self.client.post(
                "/auth/login",
                data={
                    "username": "cleanup-resilience@example.com",
                    "password": "Secret123!",
                },
            )
            self.assertEqual(login.status_code, 200)

            refresh = self.client.post(
                "/auth/refresh",
                headers={
                    "Origin": ORIGIN,
                    "X-CSRF-Token": login.json()["csrf_token"],
                },
            )
            self.assertEqual(refresh.status_code, 200)


if __name__ == "__main__":
    unittest.main()
