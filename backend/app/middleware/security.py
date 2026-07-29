import json
from collections.abc import Awaitable, Callable
from typing import Any

from starlette.datastructures import Headers, MutableHeaders


ASGIApp = Callable[[dict, Callable, Callable], Awaitable[None]]


async def _send_json_response(
    send: Callable,
    status_code: int,
    detail: str,
) -> None:
    body = json.dumps(
        {"detail": detail},
        separators=(",", ":"),
    ).encode("utf-8")
    await send(
        {
            "type": "http.response.start",
            "status": status_code,
            "headers": [
                (b"content-type", b"application/json"),
                (b"content-length", str(len(body)).encode("ascii")),
            ],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": body,
        }
    )


class RequestBodyLimitMiddleware:
    def __init__(self, app: ASGIApp, max_body_bytes: int):
        self.app = app
        self.max_body_bytes = max_body_bytes

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable,
        send: Callable,
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        content_length = headers.get("content-length")
        if content_length is not None:
            try:
                declared_size = int(content_length)
            except ValueError:
                await _send_json_response(
                    send,
                    400,
                    "Invalid Content-Length header",
                )
                return

            if declared_size < 0:
                await _send_json_response(
                    send,
                    400,
                    "Invalid Content-Length header",
                )
                return
            if declared_size > self.max_body_bytes:
                await _send_json_response(
                    send,
                    413,
                    "Request body exceeds the maximum allowed size",
                )
                return

        received_size = 0
        exceeded = False
        response_started = False

        async def limited_receive() -> dict[str, Any]:
            nonlocal exceeded, received_size
            message = await receive()

            if message["type"] == "http.request":
                received_size += len(message.get("body", b""))
                if received_size > self.max_body_bytes:
                    exceeded = True
                    return {"type": "http.disconnect"}

            return message

        async def guarded_send(message: dict[str, Any]) -> None:
            nonlocal response_started
            if not exceeded:
                if message["type"] == "http.response.start":
                    response_started = True
                await send(message)

        try:
            await self.app(scope, limited_receive, guarded_send)
        except Exception:
            if not exceeded:
                raise

        if exceeded and not response_started:
            await _send_json_response(
                send,
                413,
                "Request body exceeds the maximum allowed size",
            )


class SecurityHeadersMiddleware:
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(
        self,
        scope: dict[str, Any],
        receive: Callable,
        send: Callable,
    ) -> None:
        async def send_with_security_headers(
            message: dict[str, Any],
        ) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.setdefault("X-Content-Type-Options", "nosniff")
                headers.setdefault("X-Frame-Options", "DENY")
                headers.setdefault("Referrer-Policy", "no-referrer")
                headers.setdefault(
                    "Permissions-Policy",
                    "camera=(), geolocation=(), microphone=()",
                )
                headers.setdefault(
                    "Cross-Origin-Resource-Policy",
                    "same-site",
                )
                headers.setdefault("Cache-Control", "no-store")

            await send(message)

        await self.app(scope, receive, send_with_security_headers)
