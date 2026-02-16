"""Data sink implementations - output destinations for processed events."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any

from src.models.events import StreamEvent
from src.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class ConsoleSink(BaseWorker):
    """Logs events to stdout. Useful for debugging and demos."""

    async def process(self, event: StreamEvent) -> list[StreamEvent] | None:
        event.add_lineage(self.node_id, "console_sink", "emitted", "stdout")
        logger.info(f"[CONSOLE SINK] {json.dumps(event.data, default=str)}")
        return None  # Sinks don't produce output


class RedisSink(BaseWorker):
    """
    Stores events in Redis for dashboard consumption.

    Events are stored in a Redis Stream with the pipeline ID,
    making them queryable by the dashboard and lineage viewer.
    Older events are trimmed to keep memory bounded.
    """

    async def process(self, event: StreamEvent) -> list[StreamEvent] | None:
        event.add_lineage(self.node_id, "redis_sink", "emitted", "redis_store")

        store_key = f"flowstorm:output:{self.pipeline_id}"
        data = event.to_redis()
        data["node_id"] = self.node_id

        await self._redis.xadd(store_key, data, maxlen=10000)

        # Also publish to a pub/sub channel for real-time dashboard
        dashboard_channel = f"flowstorm:dashboard:{self.pipeline_id}"
        await self._redis.publish(dashboard_channel, json.dumps(event.data, default=str))

        return None


class AlertSink(BaseWorker):
    """
    Evaluates alert conditions and fires notifications.

    Config:
        alert_channel: "console" | "webhook" | "telegram"
        alert_webhook_url: str - URL for webhook alerts
        alert_message_template: str - template with {field} placeholders

    Every event reaching this sink triggers an alert evaluation.
    """

    def __init__(self):
        super().__init__()
        self._alerts_fired: int = 0

    async def process(self, event: StreamEvent) -> list[StreamEvent] | None:
        channel = self.operator_config.get("alert_channel", "console")
        template = self.operator_config.get(
            "alert_message_template",
            "ALERT: {data}"
        )

        # Format the alert message
        try:
            message = template.format(data=event.data, **event.data)
        except (KeyError, IndexError):
            message = f"ALERT: {json.dumps(event.data, default=str)}"

        alert_record = {
            "alert_id": f"alert-{self._alerts_fired}",
            "pipeline_id": self.pipeline_id,
            "node_id": self.node_id,
            "message": message,
            "event_data": event.data,
            "timestamp": datetime.utcnow().isoformat(),
            "channel": channel,
        }

        event.add_lineage(self.node_id, "alert_sink", "emitted", f"channel={channel}")

        if channel == "console":
            logger.warning(f"[ALERT] {message}")
        elif channel == "webhook":
            await self._send_webhook(alert_record)

        # Store alert in Redis for dashboard
        alert_key = f"flowstorm:alerts:{self.pipeline_id}"
        await self._redis.xadd(alert_key, {
            "data": json.dumps(alert_record, default=str),
        }, maxlen=1000)

        # Publish real-time alert event
        await self._redis.publish(
            f"flowstorm:alert_events:{self.pipeline_id}",
            json.dumps(alert_record, default=str),
        )

        self._alerts_fired += 1
        return None

    async def _send_webhook(self, alert_record: dict[str, Any]) -> None:
        url = self.operator_config.get("alert_webhook_url", "")
        if not url:
            logger.warning("Webhook URL not configured, skipping")
            return
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(url, json=alert_record, timeout=5.0)
        except Exception as e:
            logger.error(f"Webhook alert failed: {e}")

    async def get_state(self) -> dict[str, Any]:
        return {"alerts_fired": self._alerts_fired}


class WebhookSink(BaseWorker):
    """
    Sends events to an external HTTP endpoint.

    Config:
        alert_webhook_url: str - destination URL
    """

    async def process(self, event: StreamEvent) -> list[StreamEvent] | None:
        url = self.operator_config.get("alert_webhook_url", "")
        event.add_lineage(self.node_id, "webhook_sink", "emitted", f"url={url}")

        if not url:
            logger.warning("Webhook URL not configured")
            return None

        try:
            import httpx
            payload = {
                "pipeline_id": self.pipeline_id,
                "node_id": self.node_id,
                "event": event.data,
                "timestamp": datetime.utcnow().isoformat(),
            }
            async with httpx.AsyncClient() as client:
                await client.post(url, json=payload, timeout=5.0)
        except Exception as e:
            logger.error(f"Webhook send failed: {e}")
            await self._send_to_dlq(event, f"webhook_error: {e}")

        return None


# Sink registry
SINK_REGISTRY: dict[str, type[BaseWorker]] = {
    "console_sink": ConsoleSink,
    "redis_sink": RedisSink,
    "alert_sink": AlertSink,
    "webhook_sink": WebhookSink,
}
