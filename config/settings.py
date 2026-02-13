"""FlowStorm configuration settings."""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Server
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Redis
    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))
    REDIS_DB: int = int(os.getenv("REDIS_DB", "0"))

    # MQTT
    MQTT_BROKER_HOST: str = os.getenv("MQTT_BROKER_HOST", "localhost")
    MQTT_BROKER_PORT: int = int(os.getenv("MQTT_BROKER_PORT", "1883"))

    # Docker
    WORKER_IMAGE: str = os.getenv("WORKER_IMAGE", "flowstorm-worker:latest")
    WORKER_NETWORK: str = os.getenv("WORKER_NETWORK", "flowstorm-net")

    # Health Monitor
    HEARTBEAT_INTERVAL_MS: int = int(os.getenv("HEARTBEAT_INTERVAL_MS", "500"))
    HEARTBEAT_TIMEOUT_MS: int = int(os.getenv("HEARTBEAT_TIMEOUT_MS", "2000"))
    HEALTH_CHECK_INTERVAL_MS: int = int(os.getenv("HEALTH_CHECK_INTERVAL_MS", "1000"))

    # Optimizer
    OPTIMIZER_INTERVAL_S: int = int(os.getenv("OPTIMIZER_INTERVAL_S", "30"))
    MIN_SELECTIVITY_FOR_PUSHDOWN: float = float(os.getenv("MIN_SELECTIVITY_FOR_PUSHDOWN", "0.3"))
    CPU_THRESHOLD_FOR_PARALLEL: float = float(os.getenv("CPU_THRESHOLD_FOR_PARALLEL", "0.8"))

    # Checkpoint
    CHECKPOINT_EVERY_N_EVENTS: int = int(os.getenv("CHECKPOINT_EVERY_N_EVENTS", "1000"))

    # NLP / LLM
    LLM_API_URL: str = os.getenv("LLM_API_URL", "https://api.anthropic.com/v1/messages")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL: str = os.getenv("LLM_MODEL", "claude-sonnet-4-20250514")

    # Chaos Engine
    CHAOS_MIN_INTERVAL_S: int = int(os.getenv("CHAOS_MIN_INTERVAL_S", "5"))
    CHAOS_MAX_INTERVAL_S: int = int(os.getenv("CHAOS_MAX_INTERVAL_S", "15"))

    # SQLite
    SQLITE_DB_PATH: str = os.getenv("SQLITE_DB_PATH", "flowstorm.db")

    # WebSocket
    WS_METRICS_PUSH_INTERVAL_MS: int = int(os.getenv("WS_METRICS_PUSH_INTERVAL_MS", "500"))


settings = Settings()
