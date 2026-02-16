"""Data source implementations - ingest data into the pipeline."""

from __future__ import annotations

import asyncio
import json
import logging
import math
import random
import time
from datetime import datetime

from src.models.events import StreamEvent
from src.workers.base import BaseWorker

logger = logging.getLogger(__name__)


class MQTTSource(BaseWorker):
    """
    Ingests events from an MQTT topic.

    Config:
        mqtt_topic: str - MQTT topic to subscribe to
        mqtt_broker: str - broker hostname
        mqtt_port: int - broker port
    """

    def __init__(self):
        super().__init__()
        self._mqtt_client = None

    async def _source_loop(self) -> None:
        import paho.mqtt.client as mqtt

        topic = self.operator_config.get("mqtt_topic", "flowstorm/sensors/#")
        broker = self.operator_config.get("mqtt_broker", self.redis_host)
        port = self.operator_config.get("mqtt_port", 1883)

        # Async queue to bridge MQTT callback thread to asyncio
        queue: asyncio.Queue[StreamEvent] = asyncio.Queue(maxsize=10000)
        loop = asyncio.get_event_loop()

        def on_message(client, userdata, msg):
            try:
                payload = json.loads(msg.payload.decode())
                event = StreamEvent(
                    source_node_id=self.node_id,
                    data={
                        "topic": msg.topic,
                        **payload,
                    },
                )
                event.add_lineage(
                    self.node_id, "mqtt_source", "ingested",
                    f"topic={msg.topic}"
                )
                loop.call_soon_threadsafe(queue.put_nowait, event)
            except Exception as e:
                logger.error(f"MQTT message parse error: {e}")

        client = mqtt.Client()
        client.on_message = on_message
        client.connect(broker, port, 60)
        client.subscribe(topic)
        client.loop_start()
        self._mqtt_client = client

        logger.info(f"MQTT Source connected to {broker}:{port}, topic={topic}")

        try:
            while self._running:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=1.0)
                    await self._emit(event)
                    self._events_processed += 1
                except asyncio.TimeoutError:
                    continue
        finally:
            client.loop_stop()
            client.disconnect()

    async def process(self, event: StreamEvent) -> list[StreamEvent] | None:
        # Sources don't process incoming events
        return None


class SimulatorSource(BaseWorker):
    """
    Generates simulated IoT sensor data for testing and demos.

    Config:
        sensor_count: int - number of simulated sensors (default 10)
        interval_ms: int - milliseconds between events per sensor (default 1000)
        chaos_enabled: bool - inject anomalies randomly
    """

    async def _source_loop(self) -> None:
        sensor_count = self.operator_config.get("sensor_count", 10)
        interval_ms = self.operator_config.get("interval_ms", 1000)
        chaos_enabled = self.operator_config.get("chaos_enabled", False)
        interval = interval_ms / 1000.0

        logger.info(
            f"Simulator Source starting: {sensor_count} sensors, "
            f"{interval_ms}ms interval, chaos={'ON' if chaos_enabled else 'OFF'}"
        )

        zones = ["Zone-A", "Zone-B", "Zone-C", "Zone-D"]
        sensor_base_temps = {
            f"sensor-{i:03d}": 20 + random.uniform(-5, 15)
            for i in range(sensor_count)
        }

        while self._running:
            for i in range(sensor_count):
                sensor_id = f"sensor-{i:03d}"
                zone = zones[i % len(zones)]
                base_temp = sensor_base_temps[sensor_id]

                # Normal variation
                temp = base_temp + random.gauss(0, 1.5)
                humidity = 45 + random.gauss(0, 8)
                pressure = 1013.25 + random.gauss(0, 2)

                # Time-of-day pattern (sinusoidal)
                hour = datetime.utcnow().hour + datetime.utcnow().minute / 60.0
                temp += 5 * math.sin((hour - 6) * math.pi / 12)

                data = {
                    "sensor_id": sensor_id,
                    "zone": zone,
                    "temperature": round(temp, 2),
                    "humidity": round(max(0, min(100, humidity)), 2),
                    "pressure": round(pressure, 2),
                    "timestamp": datetime.utcnow().isoformat(),
                }

                # Chaos injection
                if chaos_enabled and random.random() < 0.05:
                    chaos_type = random.choice(["spike", "missing", "drift"])
                    if chaos_type == "spike":
                        data["temperature"] += random.uniform(20, 40)
                        data["_chaos"] = "temperature_spike"
                    elif chaos_type == "missing":
                        del data["temperature"]
                        data["_chaos"] = "missing_field"
                    elif chaos_type == "drift":
                        # Future timestamp (clock drift)
                        from datetime import timedelta
                        future = datetime.utcnow() + timedelta(hours=random.randint(1, 5))
                        data["timestamp"] = future.isoformat()
                        data["_chaos"] = "clock_drift"

                event = StreamEvent(
                    source_node_id=self.node_id,
                    data=data,
                )
                event.add_lineage(
                    self.node_id, "simulator_source", "ingested",
                    f"sensor={sensor_id}, zone={zone}"
                )
                await self._emit(event)
                self._events_processed += 1

            await asyncio.sleep(interval)

    async def process(self, event: StreamEvent) -> list[StreamEvent] | None:
        return None


# Add sources to the operator registry
SOURCE_REGISTRY: dict[str, type[BaseWorker]] = {
    "mqtt_source": MQTTSource,
    "simulator_source": SimulatorSource,
}
