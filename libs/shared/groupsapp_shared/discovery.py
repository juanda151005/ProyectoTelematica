"""Simple Consul service discovery helpers.

In Kubernetes, DNS+Service is usually enough. Consul is included so we
also satisfy the rubric's "servicio de coordinación" and "servicio de
nombres" requirements in docker-compose environments.
"""
from __future__ import annotations

import os
import socket
from typing import Optional

import httpx


class ConsulClient:
    def __init__(self, consul_url: Optional[str] = None):
        self.base = consul_url or os.getenv("CONSUL_URL", "http://consul:8500")

    def register(
        self,
        name: str,
        port: int,
        service_id: Optional[str] = None,
        host: Optional[str] = None,
        http_check_path: str = "/health",
    ) -> str:
        sid = service_id or f"{name}-{socket.gethostname()}"
        address = host or socket.gethostname()
        body = {
            "ID": sid,
            "Name": name,
            "Address": address,
            "Port": port,
            "Check": {
                "HTTP": f"http://{address}:{port}{http_check_path}",
                "Interval": "10s",
                "Timeout": "2s",
                "DeregisterCriticalServiceAfter": "1m",
            },
        }
        try:
            httpx.put(f"{self.base}/v1/agent/service/register", json=body, timeout=5.0)
        except Exception:  # pragma: no cover - best-effort
            pass
        return sid

    def deregister(self, service_id: str) -> None:
        try:
            httpx.put(f"{self.base}/v1/agent/service/deregister/{service_id}", timeout=5.0)
        except Exception:  # pragma: no cover
            pass

    def kv_get(self, key: str) -> Optional[str]:
        try:
            r = httpx.get(f"{self.base}/v1/kv/{key}?raw", timeout=3.0)
            if r.status_code == 200:
                return r.text
        except Exception:  # pragma: no cover
            pass
        return None
