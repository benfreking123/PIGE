from __future__ import annotations

import httpx


def get_client() -> httpx.AsyncClient:
    timeout = httpx.Timeout(connect=5.0, read=20.0, write=5.0, pool=5.0)
    limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)
    return httpx.AsyncClient(timeout=timeout, limits=limits)
