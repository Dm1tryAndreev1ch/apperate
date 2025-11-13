"""Custom API route supporting optional payload encryption."""
from __future__ import annotations

from typing import Callable

from fastapi import Request, Response
from fastapi.routing import APIRoute

from app.security.encryption import encryption_service


class EncryptedAPIRoute(APIRoute):
    """Route that decrypts/encrypts payloads when X-Encrypted header is set."""

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request) -> Response:
            encrypted_request = request.headers.get("X-Encrypted", "").lower() in {"1", "true", "yes"}

            if encrypted_request:
                raw_body = await request.body()
                if raw_body:
                    try:
                        # Expect base64 string
                        decrypted = encryption_service.decrypt_transport(raw_body.decode("utf-8"))
                    except Exception:
                        return Response("Invalid encrypted payload", status_code=400)

                    async def receive() -> dict:
                        return {"type": "http.request", "body": decrypted, "more_body": False}

                    request._receive = receive  # type: ignore[attr-defined]

            response: Response = await original_route_handler(request)

            content_type = response.media_type or response.headers.get("content-type", "")
            if encrypted_request and content_type and "application/json" in content_type.lower():
                if hasattr(response, "body") and response.body is not None:
                    body = response.body
                else:
                    body = b""
                    async for chunk in response.body_iterator:
                        body += chunk
                encrypted_body = encryption_service.encrypt_transport(body)
                encrypted_response = Response(
                    content=encrypted_body,
                    media_type="application/octet-stream",
                    status_code=response.status_code,
                    headers=dict(response.headers),
                )
                encrypted_response.headers["X-Encrypted"] = "true"
                return encrypted_response

            return response

        return custom_route_handler



