from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.config import get_settings
from app.consumers import handle_event
from app.database import create_all
from app.router import presence_router, users_router, ws_router
from groupsapp_shared.discovery import ConsulClient
from groupsapp_shared.events import EventBus, wait_for_broker
from groupsapp_shared.logging import setup_logging

settings = get_settings()
log = logging.getLogger(__name__)

bus = EventBus(settings.amqp_url)
consul = ConsulClient(settings.consul_url)


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging(settings.service_name)
    create_all()
    await wait_for_broker(settings.amqp_url)
    await bus.connect()
    await bus.subscribe(
        "presence.events",
        ["message.created", "message.read", "group.member.added", "group.member.removed"],
        handle_event,
    )
    sid = consul.register(settings.service_name, settings.http_port)
    log.info("%s started", settings.service_name)
    try:
        yield
    finally:
        consul.deregister(sid)
        await bus.close()


app = FastAPI(title="presence-notifications-service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.service_name}


app.include_router(users_router)
app.include_router(presence_router)
app.include_router(ws_router)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.http_port, log_level="info", ws="websockets")
