from datetime import datetime, timedelta, timezone
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    ALGORITHM,
    CSRF_COOKIE_NAME,
    JWT_AUDIENCE,
    JWT_ISSUER,
    REFRESH_COOKIE_NAME,
)
from app.core.security import SECRET_KEY
from app.main import app
from app.models.refresh_session import RefreshSession
from app.models.user import User
from app.services.auth_session import (
    cleanup_refresh_sessions,
    digest_refresh_token,
)
from tests.test_api import ApiTestCase


ORIGIN = "http://localhost:5173"


class AuthSessionTests(ApiTestCase):
    def login(self, email="session@example.com"):
        self.client.post(
            "/auth/register",
            json={"email": email, "password": "Secret123!"},
        )
        return self.client.post(
            "/auth/login",
            data={"username": email, "password": "Secret123!"},
        )

    @staticmethod
    def csrf_headers(csrf_token):
        return {
            "Origin": ORIGIN,
            "X-CSRF-Token": csrf_token,
        }

    def test_access_token_has_required_short_lived_claims(self):
        response = self.login()
        self.assertEqual(response.status_code, 200)
        payload = jwt.decode(
            response.json()["access_token"],
            SECRET_KEY,
            algorithms=[ALGORITHM],
            audience=JWT_AUDIENCE,
            issuer=JWT_ISSUER,
        )

        self.assertEqual(payload["type"], "access")
        self.assertEqual(payload["aud"], JWT_AUDIENCE)
        self.assertEqual(payload["iss"], JWT_ISSUER)
        self.assertTrue(payload["jti"])
        self.assertLessEqual(
            payload["exp"] - payload["iat"],
            ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        )

    def test_login_stores_only_a_digest_and_sets_bounded_cookies(self):
        response = self.login()
        body = response.json()
        refresh_token = response.cookies.get(REFRESH_COOKIE_NAME)
        csrf_token = response.cookies.get(CSRF_COOKIE_NAME)

        self.assertNotIn("refresh_token", body)
        self.assertEqual(body["csrf_token"], csrf_token)
        self.assertIsNotNone(refresh_token)
        set_cookie = "\n".join(response.headers.get_list("set-cookie"))
        self.assertIn("HttpOnly", set_cookie)
        self.assertIn("Path=/auth", set_cookie)
        self.assertIn("SameSite=lax", set_cookie)
        self.assertIn("Max-Age=", set_cookie)

        with self.TestingSession() as db:
            stored = db.query(RefreshSession).one()
            self.assertNotEqual(stored.token_hash, refresh_token)
            self.assertEqual(
                stored.token_hash,
                digest_refresh_token(refresh_token),
            )

    def test_refresh_rotates_token_and_replacement_remains_usable(self):
        login = self.login()
        old_refresh = login.cookies.get(REFRESH_COOKIE_NAME)
        first = self.client.post(
            "/auth/refresh",
            headers=self.csrf_headers(login.json()["csrf_token"]),
        )
        self.assertEqual(first.status_code, 200)
        replacement = first.cookies.get(REFRESH_COOKIE_NAME)
        self.assertNotEqual(replacement, old_refresh)

        second = self.client.post(
            "/auth/refresh",
            headers=self.csrf_headers(first.json()["csrf_token"]),
        )
        self.assertEqual(second.status_code, 200)

        with self.TestingSession() as db:
            sessions = db.query(RefreshSession).order_by(
                RefreshSession.id
            ).all()
            self.assertEqual(len(sessions), 3)
            self.assertEqual(sessions[0].revoke_reason, "rotated")
            self.assertEqual(sessions[0].replaced_by_id, sessions[1].id)

    def test_reusing_rotated_token_revokes_the_family(self):
        login = self.login()
        old_refresh = login.cookies.get(REFRESH_COOKIE_NAME)
        rotated = self.client.post(
            "/auth/refresh",
            headers=self.csrf_headers(login.json()["csrf_token"]),
        )
        self.assertEqual(rotated.status_code, 200)

        replay = TestClient(app)
        replay.cookies.set(
            REFRESH_COOKIE_NAME,
            old_refresh,
            domain="testserver.local",
            path="/auth",
        )
        csrf = replay.get("/auth/csrf").json()["csrf_token"]
        rejected = replay.post(
            "/auth/refresh",
            headers=self.csrf_headers(csrf),
        )
        self.assertEqual(rejected.status_code, 401)
        cleared_cookies = "\n".join(
            rejected.headers.get_list("set-cookie")
        )
        self.assertIn(f"{REFRESH_COOKIE_NAME}=", cleared_cookies)
        self.assertIn("Max-Age=0", cleared_cookies)

        with self.TestingSession() as db:
            family = db.query(RefreshSession).all()
            self.assertTrue(all(row.revoked_at is not None for row in family))
            self.assertEqual(family[-1].revoke_reason, "reuse_detected")

    def test_refresh_requires_cookie_csrf_match_and_allowed_origin(self):
        login = self.login()
        csrf = login.json()["csrf_token"]
        missing_header = self.client.post(
            "/auth/refresh",
            headers={"Origin": ORIGIN},
        )
        self.assertEqual(missing_header.status_code, 403)

        mismatch = self.client.post(
            "/auth/refresh",
            headers=self.csrf_headers("wrong"),
        )
        self.assertEqual(mismatch.status_code, 403)

        unsafe_origin = self.client.post(
            "/auth/refresh",
            headers={
                "Origin": "https://attacker.example",
                "X-CSRF-Token": csrf,
            },
        )
        self.assertEqual(unsafe_origin.status_code, 403)

        fresh = TestClient(app)
        fresh_csrf = fresh.get("/auth/csrf").json()["csrf_token"]
        missing_cookie = fresh.post(
            "/auth/refresh",
            headers=self.csrf_headers(fresh_csrf),
        )
        self.assertEqual(missing_cookie.status_code, 401)

    def test_malformed_expired_revoked_and_deleted_user_sessions_fail_safely(self):
        malformed = TestClient(app)
        malformed.cookies.set(
            REFRESH_COOKIE_NAME,
            "not-valid",
            domain="testserver.local",
            path="/auth",
        )
        malformed_csrf = malformed.get("/auth/csrf").json()["csrf_token"]
        self.assertEqual(
            malformed.post(
                "/auth/refresh",
                headers=self.csrf_headers(malformed_csrf),
            ).status_code,
            401,
        )

        login = self.login("expired@example.com")
        with self.TestingSession() as db:
            session = db.query(RefreshSession).one()
            session.expires_at = datetime.now(timezone.utc) - timedelta(
                seconds=1
            )
            db.commit()
        self.assertEqual(
            self.client.post(
                "/auth/refresh",
                headers=self.csrf_headers(login.json()["csrf_token"]),
            ).status_code,
            401,
        )

        self.client.cookies.clear()
        deleted = self.login("deleted@example.com")
        with self.TestingSession() as db:
            user = db.query(User).filter(
                User.email == "deleted@example.com"
            ).one()
            db.delete(user)
            db.commit()
        self.assertEqual(
            self.client.post(
                "/auth/refresh",
                headers=self.csrf_headers(deleted.json()["csrf_token"]),
            ).status_code,
            401,
        )

    def test_logout_revokes_family_clears_cookies_and_is_idempotent(self):
        login = self.login()
        logged_out = self.client.post(
            "/auth/logout",
            headers=self.csrf_headers(login.json()["csrf_token"]),
        )
        self.assertEqual(logged_out.status_code, 200)
        self.assertNotIn(REFRESH_COOKIE_NAME, self.client.cookies)
        self.assertNotIn(CSRF_COOKIE_NAME, self.client.cookies)

        with self.TestingSession() as db:
            session = db.query(RefreshSession).one()
            self.assertEqual(session.revoke_reason, "logout")

        repeated = self.client.post("/auth/logout")
        self.assertEqual(repeated.status_code, 200)

    def test_cleanup_is_bounded_and_retains_recent_replay_history(self):
        self.login()
        cutoff = datetime.now(timezone.utc) - timedelta(days=60)
        with self.TestingSession() as db:
            original = db.query(RefreshSession).one()
            original.expires_at = cutoff
            for index in range(105):
                db.add(
                    RefreshSession(
                        user_id=original.user_id,
                        token_hash=f"{index:064x}",
                        family_id=f"{index:032x}",
                        issued_at=cutoff,
                        expires_at=cutoff,
                    )
                )
            db.commit()
            deleted = cleanup_refresh_sessions(db)
            db.commit()
            self.assertEqual(deleted, 100)
            self.assertEqual(db.query(RefreshSession).count(), 6)

    def test_credentialed_csrf_preflight_and_security_headers_are_preserved(self):
        preflight = self.client.options(
            "/auth/refresh",
            headers={
                "Origin": ORIGIN,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "X-CSRF-Token",
            },
        )
        self.assertEqual(preflight.status_code, 200)
        self.assertEqual(
            preflight.headers["access-control-allow-origin"],
            ORIGIN,
        )
        self.assertEqual(
            preflight.headers["access-control-allow-credentials"],
            "true",
        )
        self.assertIn(
            "X-CSRF-Token".lower(),
            preflight.headers["access-control-allow-headers"].lower(),
        )

        denied = self.client.options(
            "/auth/refresh",
            headers={
                "Origin": "https://attacker.example",
                "Access-Control-Request-Method": "POST",
            },
        )
        self.assertNotEqual(denied.status_code, 200)

        login = self.login()
        refreshed = self.client.post(
            "/auth/refresh",
            headers=self.csrf_headers(login.json()["csrf_token"]),
        )
        self.assertEqual(refreshed.headers["cache-control"], "no-store")
        self.assertEqual(
            refreshed.headers["x-content-type-options"],
            "nosniff",
        )

    def test_rotation_database_failure_does_not_consume_the_session(self):
        login = self.login()
        with patch(
            "sqlalchemy.orm.Session.commit",
            side_effect=RuntimeError("database unavailable"),
        ):
            failing_client = TestClient(app, raise_server_exceptions=False)
            failing_client.cookies.update(self.client.cookies)
            failed = failing_client.post(
                "/auth/refresh",
                headers=self.csrf_headers(login.json()["csrf_token"]),
            )
        self.assertEqual(failed.status_code, 500)

        with self.TestingSession() as db:
            session = db.query(RefreshSession).one()
            self.assertIsNone(session.revoked_at)


if __name__ == "__main__":
    unittest.main()
