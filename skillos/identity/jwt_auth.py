"""Minimal HS256 JWT (stdlib only) for Sprint 1."""


import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any


class JWTError(Exception):
    pass


def _secret() -> bytes:
    key = os.getenv("SKILLOS_JWT_SECRET", "").strip()
    if not key:
        key = os.getenv("SKILLHUB_ADMIN_PASSWORD", "skillos-dev-secret-change-me")
    return key.encode()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _b64url_decode(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def issue_jwt(payload: dict[str, Any], *, ttl_seconds: int = 604800) -> str:
    """Issue a signed JWT (default TTL 7 days)."""
    header = {"alg": "HS256", "typ": "JWT"}
    body = {**payload, "exp": int(time.time()) + ttl_seconds, "iat": int(time.time())}
    segments = [
        _b64url(json.dumps(header, separators=(",", ":")).encode()),
        _b64url(json.dumps(body, separators=(",", ":")).encode()),
    ]
    signing_input = f"{segments[0]}.{segments[1]}".encode()
    sig = hmac.new(_secret(), signing_input, hashlib.sha256).digest()
    segments.append(_b64url(sig))
    return ".".join(segments)


def verify_jwt(token: str) -> dict[str, Any]:
    """Verify signature and expiry; return payload."""
    if not token or token.count(".") != 2:
        raise JWTError("invalid token format")
    header_b64, payload_b64, sig_b64 = token.split(".")
    signing_input = f"{header_b64}.{payload_b64}".encode()
    expected = hmac.new(_secret(), signing_input, hashlib.sha256).digest()
    if not hmac.compare_digest(_b64url(expected), sig_b64):
        raise JWTError("invalid signature")
    payload = json.loads(_b64url_decode(payload_b64))
    exp = payload.get("exp", 0)
    if exp and int(time.time()) > int(exp):
        raise JWTError("token expired")
    return payload
