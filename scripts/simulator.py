"""FlowStorm IoT Sensor Simulator.

Standalone script that simulates IoT sensors publishing data via MQTT.
Use this for testing and demos without real hardware.

Usage:
    python scripts/simulator.py --sensors 50 --interval 500 --chaos

Features:
- Configurable number of sensors (default 50)
- Configurable publish interval in ms (default 1000)
- Realistic sensor data with time-of-day patterns
- Optional chaos mode: random spikes, missing fields, clock drift, sensor death
- Sensors grouped into zones for spatial correlation
"""

from __future__ import annotations

import argparse
import json
import logging
import math
import random
import signal
import sys
import time
from datetime import datetime, timedelta

import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [simulator] %(levelname)s: %(message)s",
)
logger = logging.getLogger("simulator")


class SensorSimulator:
    def __init__(
        self,
        broker_host: str = "localhost",
        broker_port: int = 1883,
        topic_prefix: str = "flowstorm/sensors",
        sensor_count: int = 50,
        interval_ms: int = 1000,
        chaos_enabled: bool = False,
        chaos_intensity: float = 0.05,
    ):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.topic_prefix = topic_prefix
        self.sensor_count = sensor_count
        self.interval = interval_ms / 1000.0
        self.chaos_enabled = chaos_enabled
        self.chaos_intensity = chaos_intensity

        self.client = mqtt.Client(client_id="flowstorm-simulator")
        self._running = False
        self._total_published = 0

        # Sensor configuration
        self.zones = ["Zone-A", "Zone-B", "Zone-C", "Zone-D", "Zone-E"]
        self.sensors: dict[str, dict] = {}

        self._init_sensors()

    def _init_sensors(self):
        """Initialize sensor base readings and zone assignments."""
        for i in range(self.sensor_count):
            sensor_id = f"sensor-{i:03d}"
            zone = self.zones[i % len(self.zones)]
            floor = (i % 5) + 1

            self.sensors[sensor_id] = {
                "zone": zone,
                "floor": floor,
                "base_temp": 22 + random.uniform(-5, 15),
                "base_humidity": 45 + random.uniform(-10, 10),
                "base_pressure": 1013.25 + random.uniform(-5, 5),
                "temp_noise": random.uniform(0.5, 2.5),
                "alive": True,
            }

    def connect(self):
        """Connect to MQTT broker."""
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                logger.info(f"Connected to MQTT broker at {self.broker_host}:{self.broker_port}")
            else:
                logger.error(f"MQTT connection failed with code {rc}")

        self.client.on_connect = on_connect
        self.client.connect(self.broker_host, self.broker_port, 60)
        self.client.loop_start()

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

    def run(self):
        """Main simulation loop."""
        self.connect()
        self._running = True

        logger.info(
            f"Simulator started: {self.sensor_count} sensors, "
            f"{self.interval*1000:.0f}ms interval, "
            f"chaos={'ON' if self.chaos_enabled else 'OFF'}"
        )

        try:
            while self._running:
                batch_start = time.time()

                for sensor_id, config in self.sensors.items():
                    if not config["alive"]:
                        # Dead sensors (from chaos) occasionally come back
                        if self.chaos_enabled and random.random() < 0.01:
                            config["alive"] = True
                            logger.info(f"Sensor {sensor_id} came back online")
                        continue

                    payload = self._generate_reading(sensor_id, config)

                    if payload is not None:
                        topic = f"{self.topic_prefix}/{config['zone']}/{sensor_id}"
                        self.client.publish(topic, json.dumps(payload))
                        self._total_published += 1

                elapsed = time.time() - batch_start
                sleep_time = max(0, self.interval - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)

                # Log stats periodically
                if self._total_published % (self.sensor_count * 10) == 0:
                    logger.info(f"Published {self._total_published} events total")

        except KeyboardInterrupt:
            pass
        finally:
            self._running = False
            self.disconnect()
            logger.info(f"Simulator stopped. Total events: {self._total_published}")

    def _generate_reading(self, sensor_id: str, config: dict) -> dict | None:
        """Generate a single sensor reading with optional chaos."""
        now = datetime.utcnow()
        hour = now.hour + now.minute / 60.0

        # Base readings with realistic variation
        temp = config["base_temp"] + random.gauss(0, config["temp_noise"])
        humidity = config["base_humidity"] + random.gauss(0, 5)
        pressure = config["base_pressure"] + random.gauss(0, 1)

        # Time-of-day patterns
        # Temperature: peaks around 2PM, lowest around 5AM
        temp += 6 * math.sin((hour - 6) * math.pi / 12)
        # Humidity: inverse of temperature
        humidity -= 3 * math.sin((hour - 6) * math.pi / 12)

        # Floor-based variation (higher floors are warmer)
        temp += config["floor"] * 0.5

        data = {
            "sensor_id": sensor_id,
            "zone": config["zone"],
            "floor": config["floor"],
            "temperature": round(temp, 2),
            "humidity": round(max(0, min(100, humidity)), 2),
            "pressure": round(pressure, 2),
            "timestamp": now.isoformat(),
        }

        # Chaos injection
        if self.chaos_enabled and random.random() < self.chaos_intensity:
            data = self._inject_chaos(sensor_id, config, data)
            if data is None:
                return None

        return data

    def _inject_chaos(self, sensor_id: str, config: dict, data: dict) -> dict | None:
        """Inject various types of chaos into sensor data."""
        chaos_type = random.choices(
            ["spike", "missing_field", "clock_drift", "sensor_death",
             "duplicate_field", "wrong_type", "extreme_value"],
            weights=[25, 20, 15, 10, 10, 10, 10],
            k=1,
        )[0]

        if chaos_type == "spike":
            # Sudden temperature spike
            spike = random.uniform(20, 50)
            data["temperature"] += spike
            data["_chaos"] = "temperature_spike"
            data["_spike_amount"] = round(spike, 2)
            logger.debug(f"CHAOS: {sensor_id} temperature spike +{spike:.1f}")

        elif chaos_type == "missing_field":
            # Remove a random field
            field = random.choice(["temperature", "humidity", "pressure"])
            del data[field]
            data["_chaos"] = f"missing_{field}"
            logger.debug(f"CHAOS: {sensor_id} missing {field}")

        elif chaos_type == "clock_drift":
            # Timestamp in the future or past
            drift = timedelta(hours=random.randint(-3, 5))
            data["timestamp"] = (datetime.utcnow() + drift).isoformat()
            data["_chaos"] = "clock_drift"
            logger.debug(f"CHAOS: {sensor_id} clock drift {drift}")

        elif chaos_type == "sensor_death":
            # Sensor goes offline
            config["alive"] = False
            data["_chaos"] = "sensor_death"
            logger.info(f"CHAOS: {sensor_id} went offline")
            return None

        elif chaos_type == "duplicate_field":
            # Send temperature in both C and F (confusing)
            data["temperature_f"] = round(data["temperature"] * 9/5 + 32, 2)
            data["_chaos"] = "duplicate_field"

        elif chaos_type == "wrong_type":
            # Send string instead of number
            data["temperature"] = f"{data['temperature']} degrees"
            data["_chaos"] = "wrong_type"

        elif chaos_type == "extreme_value":
            # Physically impossible value
            data["temperature"] = random.choice([-273.15, 1000, 0, -999])
            data["_chaos"] = "extreme_value"

        return data

    def stop(self):
        self._running = False


def main():
    parser = argparse.ArgumentParser(description="FlowStorm IoT Sensor Simulator")
    parser.add_argument("--broker", default="localhost", help="MQTT broker host")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--sensors", type=int, default=50, help="Number of sensors")
    parser.add_argument("--interval", type=int, default=1000, help="Interval in ms")
    parser.add_argument("--chaos", action="store_true", help="Enable chaos mode")
    parser.add_argument(
        "--chaos-intensity", type=float, default=0.05,
        help="Chaos probability per reading (0.0-1.0)"
    )
    parser.add_argument("--topic", default="flowstorm/sensors", help="MQTT topic prefix")
    args = parser.parse_args()

    sim = SensorSimulator(
        broker_host=args.broker,
        broker_port=args.port,
        topic_prefix=args.topic,
        sensor_count=args.sensors,
        interval_ms=args.interval,
        chaos_enabled=args.chaos,
        chaos_intensity=args.chaos_intensity,
    )

    signal.signal(signal.SIGTERM, lambda *_: sim.stop())
    sim.run()


if __name__ == "__main__":
    main()
