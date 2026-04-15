"""Integration smoke test against the docker-compose stack (Traefik @ :80).

Run:
    docker compose -f deploy/docker-compose.yml up -d --build
    pytest tests/test_integration_microservices.py -v

The test verifies the full critical path across the 4 microservices and the
RabbitMQ+gRPC wiring: register -> create group -> add member -> send message
-> fetch history -> check presence.
"""
from __future__ import annotations

import os
import time
import uuid

import httpx
import pytest

BASE = os.getenv("GROUPSAPP_BASE_URL", "http://localhost")


def _unique(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


def _register(client: httpx.Client, username: str) -> dict:
    r = client.post(
        "/api/v1/auth/register",
        json={"username": username, "email": f"{username}@t.io", "password": "password123", "full_name": username},
        timeout=10.0,
    )
    assert r.status_code in (200, 201), r.text
    return r.json()


@pytest.fixture(scope="module")
def client() -> httpx.Client:
    # Wait for gateway up
    deadline = time.time() + 60
    while time.time() < deadline:
        try:
            httpx.get(f"{BASE}/api/v1/auth/register", timeout=2).status_code
            break
        except Exception:
            time.sleep(2)
    with httpx.Client(base_url=BASE) as c:
        yield c


def test_end_to_end_flow(client: httpx.Client):
    alice = _register(client, _unique("alice"))
    bob = _register(client, _unique("bob"))
    tok_a = alice["access_token"]
    tok_b = bob["access_token"]
    hdr_a = {"Authorization": f"Bearer {tok_a}"}
    hdr_b = {"Authorization": f"Bearer {tok_b}"}

    # create group as alice
    r = client.post("/api/v1/groups", json={"name": "TestGroup", "settings": {}}, headers=hdr_a)
    assert r.status_code == 201, r.text
    group_id = r.json()["id"]

    # add bob
    r = client.post(
        f"/api/v1/groups/{group_id}/members",
        json={"username": bob["user"]["username"]},
        headers=hdr_a,
    )
    assert r.status_code == 201, r.text

    # send message from alice
    r = client.post(
        f"/api/v1/groups/{group_id}/messages",
        json={"content": "hola bob"},
        headers=hdr_a,
    )
    assert r.status_code == 201, r.text

    # bob reads history (verifies gRPC IsMember path)
    r = client.get(f"/api/v1/groups/{group_id}/messages", headers=hdr_b)
    assert r.status_code == 200, r.text
    msgs = r.json()
    assert any(m["content"] == "hola bob" for m in msgs)

    # bob's presence (presence service)
    r = client.get(f"/api/v1/users/{bob['user']['id']}/presence", headers=hdr_a)
    assert r.status_code == 200, r.text
