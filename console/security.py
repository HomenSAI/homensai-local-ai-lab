"""Request guard of the console (standard library only).

The console has no user accounts and is meant for 127.0.0.1 or a trusted LAN, but a web page that the
operator opens in the same browser must not be able to drive it. The guard therefore

* accepts only Host names that cannot be the target of DNS rebinding (localhost, IP literals,
  names listed in AI_CONSOLE_ALLOWED_HOSTS),
* lets POST requests through only as `Content-Type: application/json` (a cross-site page cannot send
  that without a CORS preflight, which the console never allows) and only from the same origin,
* optionally asks for an HTTP Basic password (AI_CONSOLE_PASSWORD) on everything except /health.
"""
from __future__ import annotations

import base64
import hmac
import ipaddress
from urllib.parse import urlsplit

LOCAL_NAMES = {"localhost", "ai-console", "ai-model-console"}
OPEN_PATHS = {"/health"}

Verdict = tuple[int, str, dict[str, str]]


def host_name(value: str | None) -> str | None:
    """Host name of a Host header value or an Origin netloc: lower case, without port and brackets."""
    if not value:
        return None
    try:
        name = urlsplit("//" + value.strip()).hostname
    except ValueError:
        return None
    return name.lower() if name else None


def host_allowed(value: str | None, extra: frozenset[str] = frozenset()) -> bool:
    name = host_name(value)
    if not name:
        return False
    if name in LOCAL_NAMES or name in extra:
        return True
    try:
        ipaddress.ip_address(name)  # an IP literal cannot be rebound to another address by DNS
        return True
    except ValueError:
        return False


def parse_hosts(text: str | None) -> frozenset[str]:
    return frozenset(item.strip().lower() for item in (text or "").split(",") if item.strip())


def password_ok(header: str | None, password: str) -> bool:
    if not header or not header.lower().startswith("basic "):
        return False
    try:
        supplied = base64.b64decode(header[6:].strip(), validate=True).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return False
    _, _, secret = supplied.partition(":")  # the user name is ignored
    return hmac.compare_digest(secret.encode("utf-8"), password.encode("utf-8"))


def check(method: str, path: str, headers, password: str = "", extra_hosts: frozenset[str] = frozenset()) -> Verdict | None:
    """None when the request may proceed, else (status, message, extra response headers)."""
    clean = path.split("?", 1)[0]
    if clean in OPEN_PATHS:
        return None
    host = headers.get("Host")
    if not host_allowed(host, extra_hosts):
        return 421, "Unknown Host header. Use localhost, the IP address, or add the name to AI_CONSOLE_ALLOWED_HOSTS.", {}
    if password and not password_ok(headers.get("Authorization"), password):
        return 401, "Password required.", {"WWW-Authenticate": 'Basic realm="Local AI Server", charset="UTF-8"'}
    if method == "POST":
        mime = (headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if mime != "application/json":
            return 415, "POST needs Content-Type: application/json.", {}
        if headers.get("Sec-Fetch-Site", "same-origin") not in ("same-origin", "none"):
            return 403, "Cross-site request refused.", {}
        origin = headers.get("Origin")
        if origin and origin != "null":
            netloc = urlsplit(origin).netloc.lower()
            if netloc != (host or "").strip().lower() and not (host_name(netloc) in extra_hosts):
                return 403, "Cross-origin request refused.", {}
        elif origin == "null":
            return 403, "Cross-origin request refused.", {}
    return None


SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "Cross-Origin-Resource-Policy": "same-origin",
    "Content-Security-Policy": ("default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
                                "img-src 'self' data: blob:; font-src 'self'; connect-src 'self'; base-uri 'none'; "
                                "form-action 'self'; frame-ancestors 'none'"),
}
