from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.database import create_all
from app.router import groups_router, messages_router
from app.schemas import MessageOut
from groupsapp_shared.discovery import ConsulClient
from groupsapp_shared.events import EventBus, EventKeys, wait_for_broker
from groupsapp_shared.logging import setup_logging

settings = get_settings()
log = logging.getLogger(__name__)

bus = EventBus(settings.amqp_url)
consul = ConsulClient(settings.consul_url)


async def publish_message_created(msg: MessageOut) -> None:
    await bus.publish(EventKeys.MESSAGE_CREATED, msg.model_dump(mode="json"))


async def publish_receipts_updated(group_id, messages: list[MessageOut]) -> None:
    await bus.publish(EventKeys.MESSAGE_READ, {
        "group_id": str(group_id),
        "messages": [m.model_dump(mode="json") for m in messages],
    })


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging(settings.service_name)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    create_all()
    await wait_for_broker(settings.amqp_url)
    await bus.connect()
    sid = consul.register(settings.service_name, settings.http_port)
    log.info("%s started", settings.service_name)
    try:
        yield
    finally:
        consul.deregister(sid)
        await bus.close()


app = FastAPI(title="messages-files-service", lifespan=lifespan)


@app.get("/health")
def health():
    return {"status": "ok", "service": settings.service_name}


app.include_router(groups_router)
app.include_router(messages_router)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.http_port, log_level="info")
