"""Worker container entry point.

This is what runs inside each Docker container.
It reads the OPERATOR_TYPE env var, instantiates the correct operator,
and starts the processing loop.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from src.workers.operators import OPERATOR_REGISTRY
from src.workers.sources import SOURCE_REGISTRY
from src.workers.sinks import SINK_REGISTRY

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("flowstorm.worker")

# Combined registry of all operator types
ALL_OPERATORS = {**OPERATOR_REGISTRY, **SOURCE_REGISTRY, **SINK_REGISTRY}


def create_worker():
    """Instantiate the correct worker based on OPERATOR_TYPE env var."""
    operator_type = os.getenv("OPERATOR_TYPE", "")
    if operator_type not in ALL_OPERATORS:
        logger.error(
            f"Unknown operator type: '{operator_type}'. "
            f"Available: {list(ALL_OPERATORS.keys())}"
        )
        sys.exit(1)

    worker_class = ALL_OPERATORS[operator_type]
    return worker_class()


async def main():
    worker = create_worker()

    # Handle graceful shutdown
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(worker.stop()))

    logger.info(
        f"Starting worker: id={worker.worker_id}, "
        f"type={worker.operator_type}, node={worker.node_id}"
    )

    try:
        await worker.run()
    except KeyboardInterrupt:
        pass
    finally:
        await worker.stop()


if __name__ == "__main__":
    asyncio.run(main())
