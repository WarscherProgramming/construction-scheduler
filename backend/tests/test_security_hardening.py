from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient
from jose import jwt

from app.api.routes_auth import (
    AUTH_LOGIN_RATE_LIMIT,
    AUTH_REGISTER_RATE_LIMIT,
    login_rate_limiter,
    register_rate_limiter,
)
from app.core.config import (
    ALGORITHM,
    JWT_AUDIENCE,
    JWT_ISSUER,
    MAX_REQUEST_BODY_BYTES,
    require_secret_key,
)
from app.core.rate_limit import InMemoryRateLimiter
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    SECRET_KEY,
    hash_password,
    verify_password,
)
from app.middleware.security import (
    RequestBodyLimitMiddleware,
    SecurityHeadersMiddleware,
)
from app.main import app as fieldflow_app
from app.models.template import ScheduleTemplate
from app.models.user import User
from app.services.pdf_export import (
    build_project_schedule_pdf,
    remove_export_file,
    safe_export_filename,
)
from tests.test_api import ApiTestCase


def bearer_token(claims: dict) -> dict[str, str]:
    payload = {
        "aud": JWT_AUDIENCE,
        "sub": "security@example.com",
        "user_id": 1,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=5),
        "iat": datetime.now(timezone.utc),
        "iss": JWT_ISSUER,
        "jti": "0123456789abcdef0123456789abcdef",
        "type": "access",
        **claims,
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


class IdentitySecurityTests(ApiTestCase):
    def test_registration_and_login_use_canonical_email_identity(self):
        created = self.client.post(
            "/auth/register",
            json={
                "email": "  Mixed.Case@Example.COM  ",
                "password": "Secret123!",
            },
        )
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json()["email"], "mixed.case@example.com")

        login = self.client.post(
            "/auth/login",
            data={
                "username": " MIXED.CASE@EXAMPLE.COM ",
                "password": "Secret123!",
            },
        )
        self.assertEqual(login.status_code, 200)

        duplicate = self.client.post(
            "/auth/register",
            json={
                "email": "Mixed.Case@Example.com",
                "password": "Secret123!",
            },
        )
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(duplicate.json()["detail"], "Unable to create account")

        malformed = self.client.post(
            "/auth/register",
            json={"email": "not-an-email", "password": "Secret123!"},
        )
        self.assertEqual(malformed.status_code, 422)
        self.assertIn(
            "Enter a valid email address",
            str(malformed.json()),
        )

    def test_password_validation_uses_the_bcrypt_byte_boundary(self):
        ascii_72 = "a" * 72
        accepted = self.client.post(
            "/auth/register",
            json={"email": "ascii@example.com", "password": ascii_72},
        )
        self.assertEqual(accepted.status_code, 201)
        self.assertEqual(
            self.client.post(
                "/auth/login",
                data={"username": "ascii@example.com", "password": ascii_72},
            ).status_code,
            200,
        )
        truncated_collision = self.client.post(
            "/auth/login",
            data={
                "username": "ascii@example.com",
                "password": ascii_72 + "x",
            },
        )
        self.assertEqual(truncated_collision.status_code, 401)

        ascii_73 = self.client.post(
            "/auth/register",
            json={"email": "long@example.com", "password": "a" * 73},
        )
        self.assertEqual(ascii_73.status_code, 422)

        unicode_72 = "é" * 36
        self.assertEqual(
            self.client.post(
                "/auth/register",
                json={
                    "email": "unicode@example.com",
                    "password": unicode_72,
                },
            ).status_code,
            201,
        )
        unicode_74 = self.client.post(
            "/auth/register",
            json={"email": "unicode2@example.com", "password": "é" * 37},
        )
        self.assertEqual(unicode_74.status_code, 422)

        with self.assertRaises(ValueError):
            hash_password("a" * 73)
        password_hash = hash_password("a" * 72)
        self.assertFalse(verify_password("a" * 73, password_hash))

    def test_missing_user_performs_dummy_verification_and_is_generic(self):
        with patch(
            "app.api.routes_auth.verify_password",
            wraps=verify_password,
        ) as verify:
            missing = self.client.post(
                "/auth/login",
                data={
                    "username": "missing@example.com",
                    "password": "Secret123!",
                },
            )

        self.assertEqual(missing.status_code, 401)
        self.assertEqual(
            missing.json()["detail"],
            "Invalid email or password",
        )
        self.assertEqual(verify.call_args.args[1], DUMMY_PASSWORD_HASH)

        self.client.post(
            "/auth/register",
            json={
                "email": "known@example.com",
                "password": "Secret123!",
            },
        )
        wrong = self.client.post(
            "/auth/login",
            data={
                "username": "known@example.com",
                "password": "WrongPassword!",
            },
        )
        self.assertEqual(wrong.status_code, missing.status_code)
        self.assertEqual(wrong.json(), missing.json())

    def test_current_user_rejects_deleted_expired_and_tampered_tokens(self):
        self.client.post(
            "/auth/register",
            json={
                "email": "security@example.com",
                "password": "Secret123!",
            },
        )
        valid = bearer_token({})
        self.assertEqual(
            self.client.get("/projects", headers=valid).status_code,
            200,
        )

        expired = bearer_token(
            {"exp": datetime.now(timezone.utc) - timedelta(seconds=1)}
        )
        self.assertEqual(
            self.client.get("/projects", headers=expired).status_code,
            401,
        )

        raw_token = valid["Authorization"].removeprefix("Bearer ")
        tampered = {"Authorization": f"Bearer {raw_token}x"}
        self.assertEqual(
            self.client.get("/projects", headers=tampered).status_code,
            401,
        )

        with self.TestingSession() as db:
            db.query(User).delete()
            db.commit()
        deleted = self.client.get("/projects", headers=valid)
        self.assertEqual(deleted.status_code, 401)
        self.assertEqual(
            deleted.json()["detail"],
            "Invalid authentication credentials",
        )

    def test_current_user_rejects_missing_malformed_and_conflicting_claims(self):
        self.client.post(
            "/auth/register",
            json={
                "email": "security@example.com",
                "password": "Secret123!",
            },
        )
        claim_sets = [
            {"user_id": None},
            {"user_id": "1"},
            {"user_id": True},
            {"user_id": -1},
            {"sub": None},
            {"sub": "other@example.com"},
            {"sub": "SECURITY@example.com"},
            {"exp": None},
            {"iat": None},
            {"jti": None},
            {"type": "refresh"},
            {"iss": "other-api"},
            {"aud": "other-client"},
        ]

        for claims in claim_sets:
            with self.subTest(claims=claims):
                response = self.client.get(
                    "/projects",
                    headers=bearer_token(claims),
                )
                self.assertEqual(response.status_code, 401)
                self.assertEqual(
                    response.json()["detail"],
                    "Invalid authentication credentials",
                )

        missing_exp_token = jwt.encode(
            {
                "sub": "security@example.com",
                "user_id": 1,
            },
            SECRET_KEY,
            algorithm=ALGORITHM,
        )
        missing_exp = self.client.get(
            "/projects",
            headers={"Authorization": f"Bearer {missing_exp_token}"},
        )
        self.assertEqual(missing_exp.status_code, 401)

    def test_secret_key_rejects_short_and_placeholder_values(self):
        for secret in (
            "short",
            "change-me-to-at-least-32-random-characters",
            "replace-with-a-long-random-secret",
        ):
            with (
                self.subTest(secret=secret),
                patch.dict(os.environ, {"SECRET_KEY": secret}),
                self.assertRaises(RuntimeError),
            ):
                require_secret_key()


class AuthenticationRateLimitTests(ApiTestCase):
    def test_login_limit_returns_retry_after_and_success_resets_bucket(self):
        self.client.post(
            "/auth/register",
            json={
                "email": "limited@example.com",
                "password": "Secret123!",
            },
        )

        for _ in range(AUTH_LOGIN_RATE_LIMIT):
            response = self.client.post(
                "/auth/login",
                data={
                    "username": "limited@example.com",
                    "password": "WrongPassword!",
                },
            )
            self.assertEqual(response.status_code, 401)

        limited = self.client.post(
            "/auth/login",
            data={
                "username": "limited@example.com",
                "password": "WrongPassword!",
            },
        )
        self.assertEqual(limited.status_code, 429)
        self.assertGreaterEqual(int(limited.headers["Retry-After"]), 1)

        login_rate_limiter.clear()
        for _ in range(AUTH_LOGIN_RATE_LIMIT - 1):
            self.client.post(
                "/auth/login",
                data={
                    "username": "limited@example.com",
                    "password": "WrongPassword!",
                },
            )
        success = self.client.post(
            "/auth/login",
            data={
                "username": "limited@example.com",
                "password": "Secret123!",
            },
        )
        self.assertEqual(success.status_code, 200)
        self.assertEqual(
            self.client.post(
                "/auth/login",
                data={
                    "username": "limited@example.com",
                    "password": "WrongPassword!",
                },
            ).status_code,
            401,
        )

    def test_registration_limit_is_independent_and_identity_scoped(self):
        self.client.post(
            "/auth/register",
            json={
                "email": "registered@example.com",
                "password": "Secret123!",
            },
        )

        for _ in range(AUTH_REGISTER_RATE_LIMIT):
            response = self.client.post(
                "/auth/register",
                json={
                    "email": "registered@example.com",
                    "password": "Secret123!",
                },
            )
            self.assertEqual(response.status_code, 400)

        limited = self.client.post(
            "/auth/register",
            json={
                "email": "registered@example.com",
                "password": "Secret123!",
            },
        )
        self.assertEqual(limited.status_code, 429)
        self.assertIn("Retry-After", limited.headers)

        separate = self.client.post(
            "/auth/register",
            json={
                "email": "separate@example.com",
                "password": "Secret123!",
            },
        )
        self.assertEqual(separate.status_code, 201)

        missing_login = self.client.post(
            "/auth/login",
            data={
                "username": "registered@example.com",
                "password": "WrongPassword!",
            },
        )
        self.assertEqual(missing_login.status_code, 401)

    def test_limiter_prunes_and_bounds_identity_entries(self):
        now = [0.0]
        limiter = InMemoryRateLimiter(
            max_entries=2,
            clock=lambda: now[0],
        )
        limiter.consume("one", limit=2, window_seconds=10)
        now[0] = 1
        limiter.consume("two", limit=2, window_seconds=10)
        now[0] = 2
        limiter.consume("three", limit=2, window_seconds=10)
        self.assertEqual(limiter.entry_count, 2)

        now[0] = 20
        limiter.consume("four", limit=2, window_seconds=10)
        self.assertEqual(limiter.entry_count, 1)


class RequestLimitAndHeaderTests(ApiTestCase):
    @staticmethod
    def build_limited_app(max_body_bytes=64):
        limited_app = FastAPI()
        calls = {"count": 0}

        @limited_app.post("/body")
        async def read_body(request: Request):
            calls["count"] += 1
            return {"size": len(await request.body())}

        limited_app.add_middleware(
            RequestBodyLimitMiddleware,
            max_body_bytes=max_body_bytes,
        )
        limited_app.add_middleware(SecurityHeadersMiddleware)
        return limited_app, calls

    def test_content_length_boundary_rejects_before_route_logic(self):
        limited_app, calls = self.build_limited_app()
        with TestClient(limited_app) as client:
            accepted = client.post("/body", content=b"a" * 64)
            rejected = client.post("/body", content=b"a" * 65)

        self.assertEqual(accepted.status_code, 200)
        self.assertEqual(accepted.json(), {"size": 64})
        self.assertEqual(rejected.status_code, 413)
        self.assertEqual(
            rejected.json(),
            {"detail": "Request body exceeds the maximum allowed size"},
        )
        self.assertEqual(calls["count"], 1)

    def test_missing_content_length_is_stream_limited(self):
        limited_app, calls = self.build_limited_app()
        with TestClient(limited_app) as client:
            response = client.post(
                "/body",
                content=(chunk for chunk in [b"a" * 40, b"b" * 30]),
            )

        self.assertEqual(response.status_code, 413)
        self.assertEqual(calls["count"], 1)

    def test_oversized_attachment_is_rejected_before_authentication(self):
        headers = {
            "Content-Type": "multipart/form-data; boundary=test",
            "Content-Length": str(MAX_REQUEST_BODY_BYTES + 1),
            "Origin": "http://localhost:5173",
        }
        unauthenticated = self.client.post(
            "/projects/1/attachments",
            content=b"--test--\r\n",
            headers=headers,
        )
        self.assertEqual(unauthenticated.status_code, 413)
        self.assertEqual(
            unauthenticated.headers["access-control-allow-origin"],
            "http://localhost:5173",
        )

        owner = self.register_and_login()
        project_id = self.create_project(owner)
        authenticated = self.client.post(
            f"/projects/{project_id}/attachments",
            content=b"--test--\r\n",
            headers={**headers, **owner},
        )
        self.assertEqual(authenticated.status_code, 413)

    def test_middleware_order_keeps_headers_and_cors_outside_body_limit(self):
        self.assertEqual(
            [item.cls for item in fieldflow_app.user_middleware],
            [
                SecurityHeadersMiddleware,
                CORSMiddleware,
                RequestBodyLimitMiddleware,
            ],
        )

    def test_security_headers_cover_normal_auth_and_error_responses(self):
        responses = [
            self.client.get("/"),
            self.client.get("/projects"),
            self.client.get("/not-found"),
            self.client.post(
                "/auth/login",
                data={
                    "username": "missing@example.com",
                    "password": "Secret123!",
                },
            ),
        ]

        for response in responses:
            with self.subTest(status=response.status_code):
                self.assertEqual(
                    response.headers["X-Content-Type-Options"],
                    "nosniff",
                )
                self.assertEqual(response.headers["X-Frame-Options"], "DENY")
                self.assertEqual(
                    response.headers["Referrer-Policy"],
                    "no-referrer",
                )
                self.assertEqual(response.headers["Cache-Control"], "no-store")


class PdfExportSecurityTests(ApiTestCase):
    def test_export_escapes_markup_uses_safe_name_and_cleans_file(self):
        headers = self.register_and_login()
        malicious_name = (
            '<img src="file:///etc/passwd">&'
            '<img src="http://127.0.0.1:8000">'
        )
        project_id = self.create_project(headers, malicious_name)
        self.client.post(
            f"/projects/{project_id}/tasks",
            json={
                "name": "<link href='file:///secret'>"
                + "<nested>" * 40,
                "duration": 1,
            },
            headers=headers,
        )

        generated_paths: list[Path] = []
        generated_options: list[dict] = []
        actual_builder = build_project_schedule_pdf

        def capture_path(project, tasks, **options):
            path = actual_builder(project, tasks, **options)
            generated_paths.append(path)
            generated_options.append(options)
            return path

        with (
            patch(
                "app.api.routes_export.build_project_schedule_pdf",
                side_effect=capture_path,
            ),
            patch(
                "reportlab.platypus.paraparser.ImageReader",
                side_effect=AssertionError("resource loading is forbidden"),
            ) as image_reader,
        ):
            response = self.client.get(
                f"/projects/{project_id}/export/pdf",
                headers=headers,
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertFalse(image_reader.called)
        self.assertRegex(generated_options[0]["data_date"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertTrue(generated_paths)
        self.assertTrue(all(not path.exists() for path in generated_paths))
        disposition = response.headers["content-disposition"]
        self.assertNotIn("<", disposition)
        self.assertNotIn("file:", disposition)

    def test_generation_failure_cleans_pdf_and_preserves_unrelated_files(self):
        with tempfile.TemporaryDirectory() as directory:
            unrelated = Path(directory) / "unrelated.txt"
            unrelated.write_text("keep", encoding="utf-8")

            project = type("Project", (), {"id": 1, "name": "Project"})()
            with (
                patch(
                    "app.services.pdf_export.tempfile.tempdir",
                    directory,
                ),
                patch(
                    "app.services.pdf_export.SimpleDocTemplate.build",
                    side_effect=RuntimeError("generation failed"),
                ),
            ):
                with self.assertRaises(RuntimeError):
                    build_project_schedule_pdf(project, [])

            self.assertTrue(unrelated.exists())
            self.assertEqual(
                [path.name for path in Path(directory).iterdir()],
                ["unrelated.txt"],
            )

    def test_generation_failure_returns_a_path_safe_error(self):
        headers = self.register_and_login()
        project_id = self.create_project(headers)
        with patch(
            "app.api.routes_export.build_project_schedule_pdf",
            side_effect=RuntimeError(r"C:\sensitive\export.pdf"),
        ):
            response = self.client.get(
                f"/projects/{project_id}/export/pdf",
                headers=headers,
            )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {"detail": "Unable to generate project schedule PDF"},
        )
        self.assertNotIn("sensitive", response.text)

    def test_safe_filename_has_a_bounded_fallback(self):
        filename = safe_export_filename("../../<img>\0", 42)
        self.assertEqual(filename, "img_schedule.pdf")
        self.assertNotIn("/", filename)
        self.assertLessEqual(len(filename), 93)
        self.assertEqual(
            safe_export_filename("施工計画", 42),
            "project-42_schedule.pdf",
        )

    def test_export_preserves_project_ownership(self):
        owner = self.register_and_login("owner@example.com")
        intruder = self.register_and_login("intruder@example.com")
        project_id = self.create_project(owner)

        response = self.client.get(
            f"/projects/{project_id}/export/pdf",
            headers=intruder,
        )
        self.assertEqual(response.status_code, 403)


class TemplateAndTaskIsolationTests(ApiTestCase):
    def test_templates_are_owner_scoped_and_foreign_apply_is_hidden(self):
        owner = self.register_and_login("owner@example.com")
        other = self.register_and_login("other@example.com")
        owner_project = self.create_project(owner, "Owner")
        other_project = self.create_project(other, "Other")
        self.client.post(
            f"/projects/{owner_project}/tasks",
            json={"name": "Private owner task", "duration": 1},
            headers=owner,
        )

        created = self.client.post(
            f"/projects/{owner_project}/templates",
            json={"name": "Owner template"},
            headers=owner,
        )
        self.assertEqual(created.status_code, 201)
        template_id = created.json()["id"]

        with self.TestingSession() as db:
            template = db.get(ScheduleTemplate, template_id)
            owner_user = (
                db.query(User).filter(User.email == "owner@example.com").one()
            )
            self.assertEqual(template.user_id, owner_user.id)
            db.add(ScheduleTemplate(name="Legacy unowned", user_id=None))
            db.commit()

        self.assertEqual(
            self.client.get("/templates", headers=owner).json(),
            {
                "templates": [
                    {"id": template_id, "name": "Owner template"}
                ]
            },
        )
        self.assertEqual(
            self.client.get("/templates", headers=other).json(),
            {"templates": []},
        )

        foreign = self.client.post(
            (
                f"/projects/{other_project}/templates/"
                f"{template_id}/apply"
            ),
            headers=other,
        )
        self.assertEqual(foreign.status_code, 404)
        self.assertEqual(foreign.json()["detail"], "Template not found")
        self.assertEqual(
            self.client.get(
                f"/projects/{other_project}/tasks",
                headers=other,
            ).json()["tasks"],
            [],
        )

    def test_missing_template_apply_returns_not_found(self):
        headers = self.register_and_login()
        project_id = self.create_project(headers)
        response = self.client.post(
            f"/projects/{project_id}/templates/9999/apply",
            headers=headers,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Template not found")

    def test_missing_and_wrong_project_task_mutations_return_not_found(self):
        headers = self.register_and_login()
        first_project = self.create_project(headers, "First")
        second_project = self.create_project(headers, "Second")
        created = self.client.post(
            f"/projects/{second_project}/tasks",
            json={"name": "Other task", "duration": 1},
            headers=headers,
        )
        foreign_task_id = created.json()["tasks"][0]["id"]

        for method in ("put", "delete"):
            with self.subTest(method=method, task="missing"):
                kwargs = (
                    {"json": {"name": "Updated"}}
                    if method == "put"
                    else {}
                )
                response = getattr(self.client, method)(
                    f"/projects/{first_project}/tasks/9999",
                    headers=headers,
                    **kwargs,
                )
                self.assertEqual(response.status_code, 404)

            with self.subTest(method=method, task="foreign"):
                kwargs = (
                    {"json": {"name": "Updated"}}
                    if method == "put"
                    else {}
                )
                response = getattr(self.client, method)(
                    (
                        f"/projects/{first_project}/tasks/"
                        f"{foreign_task_id}"
                    ),
                    headers=headers,
                    **kwargs,
                )
                self.assertEqual(response.status_code, 404)

    def test_reorder_rejects_invalid_ids_without_partial_changes(self):
        headers = self.register_and_login()
        project_id = self.create_project(headers, "First")
        other_project = self.create_project(headers, "Other")

        first = self.client.post(
            f"/projects/{project_id}/tasks",
            json={"name": "First", "duration": 1},
            headers=headers,
        ).json()["tasks"][0]["id"]
        second = self.client.post(
            f"/projects/{project_id}/tasks",
            json={"name": "Second", "duration": 1},
            headers=headers,
        ).json()["tasks"][-1]["id"]
        foreign = self.client.post(
            f"/projects/{other_project}/tasks",
            json={"name": "Foreign", "duration": 1},
            headers=headers,
        ).json()["tasks"][0]["id"]

        invalid = self.client.put(
            f"/projects/{project_id}/tasks/reorder",
            json={"task_ids": [second, foreign]},
            headers=headers,
        )
        self.assertEqual(invalid.status_code, 404)
        tasks = self.client.get(
            f"/projects/{project_id}/tasks",
            headers=headers,
        ).json()["tasks"]
        self.assertEqual([task["id"] for task in tasks], [first, second])

        duplicate = self.client.put(
            f"/projects/{project_id}/tasks/reorder",
            json={"task_ids": [first, first]},
            headers=headers,
        )
        self.assertEqual(duplicate.status_code, 422)


if __name__ == "__main__":
    unittest.main()
