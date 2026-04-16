"""RabbitMQ event bus wrapper (aio-pika).

Topic exchange ``groupsapp.events`` is the single bus for inter-service
events. Producers publish with a routing key (e.g. ``message.created``);
consumers declare a queue and bind with a routing-key pattern.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Awaitable, Callable, Optional

import aio_pika

log = logging.getLogger(__name__)

EXCHANGE_NAME = "groupsapp.events"


class EventBus:
    def __init__(self, amqp_url: str):
        self.amqp_url = amqp_url
        self._connection: Optional[aio_pika.RobustConnection] = None
        self._channel: Optional[aio_pika.abc.AbstractRobustChannel] = None
        self._exchange: Optional[aio_pika.abc.AbstractExchange] = None

    async def connect(self) -> None:
        self._connection = await aio_pika.connect_robust(self.amqp_url)
        self._channel = await self._connection.channel()
        await self._channel.set_qos(prefetch_count=32)
        self._exchange = await self._channel.declare_exchange(
            EXCHANGE_NAME, aio_pika.ExchangeType.TOPIC, durable=True
        )
        log.info("EventBus connected: %s", self.amqp_url)

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()

    async def publish(self, routing_key: str, payload: dict) -> None:
        assert self._exchange is not None, "EventBus not connected"
        body = json.dumps(payload, default=str).encode("utf-8")
        message = aio_pika.Message(
            body=body,
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
        )
        await self._exchange.publish(message, routing_key=routing_key)
        log.debug("published %s -> %s", routing_key, payload)

    async def subscribe(
        self,
        queue_name: str,
        routing_keys: list[str],
        handler: Callable[[str, dict], Awaitable[None]],
    ) -> None:
        assert self._channel is not None and self._exchange is not None
        queue = await self._channel.declare_queue(queue_name, durable=True)
        for rk in routing_keys:
            await queue.bind(self._exchange, routing_key=rk)

        async def _on_message(message: aio_pika.abc.AbstractIncomingMessage) -> None:
            async with message.process(requeue=False):
                try:
                    payload = json.loads(message.body.decode("utf-8"))
                    await handler(message.routing_key or "", payload)
                except Exception:  # noqa: BLE001
                    log.exception("error handling event %s", message.routing_key)

        await queue.consume(_on_message)
        log.info("subscribed queue=%s keys=%s", queue_name, routing_keys)


async def wait_for_broker(amqp_url: str, max_attempts: int = 30) -> None:
    """Busy-wait until RabbitMQ accepts connections (used at service start)."""
    for attempt in range(max_attempts):
        try:
            conn = await aio_pika.connect_robust(amqp_url, timeout=3)
            await conn.close()
            return
        except Exception:  # noqa: BLE001
            await asyncio.sleep(2)
    raise RuntimeError(f"RabbitMQ not reachable at {amqp_url}")


# Routing keys (single source of truth)
class EventKeys:
    USER_CREATED = "user.created"
    GROUP_CREATED = "group.created"
    GROUP_MEMBER_ADDED = "group.member.added"
    MESSAGE_CREATED = "message.created"
    MESSAGE_READ = "message.read"
    PRESENCE_CHANGED = "presence.changed"
