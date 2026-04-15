from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from app.config import get_settings
from app.consumers import handle_event
from app.database import create_all
from app.grpc_server import serve_grpc
from app.router import router
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
    await bus.subscribe("groups.message.created", ["message.created"], handle_event)
    grpc_task = asyncio.create_task(serve_grpc())
    sid = consul.register(settings.service_name, settings.http_port)
    log.info("%s started", settings.service_name)
    try:
        yield
    finally:
        grpc_task.cancel()
        consul.deregister(sid)
        await bus.close()


app = FastAPI(title="groups-service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.service_name}


app.include_router(router)


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.http_port, log_level="info")
