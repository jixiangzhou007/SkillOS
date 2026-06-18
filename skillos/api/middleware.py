"""Production middleware — rate limiting, security headers, request logging."""

import hashlib
import time
import threading
from typing import Optional


# ═══════════════════════════════════════════════════════════════
# Rate Limiter
# ═══════════════════════════════════════════════════════════════

class RateLimiter:
    """Simple in-memory rate limiter with sliding window.

    Default: 60 requests per minute per client.
    """

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._clients: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def is_allowed(self, client_id: str) -> tuple[bool, int]:
        """Check if client is within rate limit.

        Returns (allowed, remaining_requests).
        """
        now = time.time()
        with self._lock:
            if client_id not in self._clients:
                self._clients[client_id] = []

            # Remove expired timestamps
            window_start = now - self.window_seconds
            self._clients[client_id] = [
                t for t in self._clients[client_id] if t > window_start
            ]

            count = len(self._clients[client_id])
            if count >= self.max_requests:
                return False, 0

            self._clients[client_id].append(now)
            return True, self.max_requests - count - 1

    def cleanup(self):
        """Periodic cleanup of old client entries."""
        now = time.time()
        window_start = now - self.window_seconds * 2
        with self._lock:
            expired = [
                cid for cid, timestamps in self._clients.items()
                if not any(t > window_start for t in timestamps)
            ]
            for cid in expired:
                del self._clients[cid]


# Global rate limiter instance
_limiter = RateLimiter()


def get_client_id(headers: dict) -> str:
    """Extract a unique client identifier from request headers."""
    # Prefer Authorization token, fall back to IP + User-Agent
    auth = headers.get("authorization", "") or headers.get("Authorization", "")
    if auth:
        return hashlib.sha256(auth.encode()).hexdigest()[:16]
    ip = headers.get("x-forwarded-for", headers.get("x-real-ip", "127.0.0.1"))
    ua = headers.get("user-agent", "unknown")
    return hashlib.sha256(f"{ip}:{ua}".encode()).hexdigest()[:16]


def check_rate_limit(headers: dict) -> tuple[bool, int]:
    """Check rate limit for a request. Returns (allowed, remaining)."""
    return _limiter.is_allowed(get_client_id(headers))


# ═══════════════════════════════════════════════════════════════
# Token Hashing
# ═══════════════════════════════════════════════════════════════

def hash_token(token: str) -> str:
    """Hash a token for storage. Uses SHA-256 with salt."""
    return hashlib.sha256(f"skillos_token:{token}:salt_v1".encode()).hexdigest()


def verify_token(token: str, stored_hash: str) -> bool:
    """Verify a token against its stored hash."""
    return hash_token(token) == stored_hash


# ═══════════════════════════════════════════════════════════════
# Skill Security Scanner
# ═══════════════════════════════════════════════════════════════

DANGEROUS_PATTERNS = [
    (r'<script[ >]', 'Embedded script tag (XSS vector)'),
    (r'onerror\s*=', 'onerror handler (XSS vector)'),
    (r'onload\s*=', 'onload handler (XSS vector)'),
    (r'(?:curl|wget)\s+.*\|\s*(?:bash|sh)', 'curl/wget piped to shell (RCE)'),
    (r'(?:subprocess|os\.system|os\.popen)\s*\(', 'Shell execution command'),
    (r'(?:eval|exec)\s*\(', 'Dynamic code execution'),
    (r'(?:import\s+requests|import\s+urllib).*\.(?:get|post)\s*\(', 'Unvalidated outbound HTTP request'),
    (r'[A-Za-z0-9+/]{40,}={0,2}', 'Potential encoded payload (base64 blob)'),
    (r'https?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', 'Hardcoded IP address URL'),
    (r'(?:api_key|api_secret|password|token|secret)\s*[=:]\s*[\'"][^\'"]{8,}', 'Hardcoded credential'),
]


def scan_skill_security(skill_content: str) -> list[dict]:
    """Scan skill content for security issues.

    Returns list of findings: [{pattern, description, match_preview}]
    """
    import re
    findings = []
    for pattern, desc in DANGEROUS_PATTERNS:
        matches = re.findall(pattern, skill_content, re.IGNORECASE)
        for m in matches[:3]:  # Limit per pattern
            preview = str(m)[:80] if isinstance(m, str) else str(m)[:80]
            findings.append({
                "pattern": pattern,
                "description": desc,
                "match": preview,
            })
    return findings


def scan_skill_file(skill_name: str) -> list[dict]:
    """Load and scan a skill for security issues."""
    try:
        from skillos.skills.skill_store import load_skill
        content = load_skill(skill_name)
        return scan_skill_security(content)
    except Exception as e:
        return [{"error": str(e)}]
