"""Tests for encryption utilities and encrypted routes."""
import json

from app.security.encryption import encryption_service


def test_encrypt_decrypt_roundtrip():
    """EncryptionService should round-trip plaintext without loss."""
    plaintext = "sensitive-secret"
    token = encryption_service.encrypt_text(plaintext)

    assert token != plaintext
    assert isinstance(token, str)

    decrypted = encryption_service.decrypt_text(token)
    assert decrypted == plaintext


def test_encrypted_route_response(client, auth_headers):
    """Endpoints should return encrypted responses when header is set."""
    headers = {**auth_headers, "X-Encrypted": "true"}
    response = client.get("/api/v1/checks", headers=headers)

    assert response.status_code == 200
    assert response.headers.get("X-Encrypted") == "true"

    decrypted_bytes = encryption_service.decrypt_transport(response.text)
    payload = json.loads(decrypted_bytes.decode("utf-8"))

    assert isinstance(payload, list)

