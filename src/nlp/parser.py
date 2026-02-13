"""NLP Parser - converts natural language commands to pipeline operations.

Uses an LLM API to parse English commands like:
  "Add a filter after the source that drops events where temperature < 20"
into structured DAG mutations.
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from config.settings import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are FlowStorm's pipeline assistant. You parse natural language commands
into structured JSON pipeline operations.

Available operator types:
- filter: Filters events. Config: field, condition (gt/lt/eq/neq/gte/lte/contains), value
- map: Transforms events. Config: expression (Python expr, x = input value), field, output_field
- window: Time-based grouping. Config: window_type (tumbling/sliding), window_size_seconds, agg_field, agg_function (avg/sum/min/max/count), group_by
- aggregate: Running aggregate. Config: agg_function, agg_field, group_by
- join: Stream join. Config: join_key, join_window_seconds
- mqtt_source: MQTT data source. Config: mqtt_topic
- simulator_source: Fake data source. Config: sensor_count, interval_ms, chaos_enabled
- console_sink: Log to console
- redis_sink: Store in Redis
- alert_sink: Fire alerts. Config: alert_channel, alert_message_template

Available actions:
- add_node: Add a new operator node
- remove_node: Remove a node by ID or label
- modify_node: Change a node's config
- add_edge: Connect two nodes
- remove_edge: Disconnect two nodes
- scale_node: Change parallelism of a node

Respond with a JSON object:
{
  "interpretation": "Human-readable description of what you understood",
  "actions": [
    {
      "action": "add_node",
      "node": {
        "label": "Temperature Filter",
        "operator_type": "filter",
        "config": {"field": "temperature", "condition": "gt", "value": 30}
      },
      "connect_after": "node_id_or_label",
      "connect_before": "node_id_or_label"
    }
  ]
}

Only respond with valid JSON. No explanations outside the JSON."""


class NLPParser:
    """Parses natural language commands into pipeline operations."""

    def __init__(self):
        self.api_url = settings.LLM_API_URL
        self.api_key = settings.LLM_API_KEY
        self.model = settings.LLM_MODEL

    async def parse(
        self,
        command: str,
        current_pipeline: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Parse a natural language command given the current pipeline state.

        Args:
            command: The user's English command
            current_pipeline: Current DAG snapshot (nodes and edges)

        Returns:
            Structured dict with interpretation and actions
        """
        if not self.api_key:
            return self._fallback_parse(command, current_pipeline)

        user_message = f"""Current pipeline state:
{json.dumps(current_pipeline, indent=2, default=str)}

User command: "{command}"

Parse this command into pipeline operations."""

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "x-api-key": self.api_key,
                        "content-type": "application/json",
                        "anthropic-version": "2023-06-01",
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 1024,
                        "system": SYSTEM_PROMPT,
                        "messages": [
                            {"role": "user", "content": user_message}
                        ],
                    },
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    content = data["content"][0]["text"]
                    result = json.loads(content)
                    logger.info(f"NLP parsed: {result.get('interpretation', '')}")
                    return result
                else:
                    logger.error(f"LLM API error {response.status_code}: {response.text}")
                    return self._fallback_parse(command, current_pipeline)

        except Exception as e:
            logger.error(f"NLP parse error: {e}")
            return self._fallback_parse(command, current_pipeline)

    def _fallback_parse(
        self, command: str, current_pipeline: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Rule-based fallback parser for when LLM API is unavailable.
        Handles common patterns.
        """
        command_lower = command.lower().strip()

        # Pattern: "add a filter ... where FIELD CONDITION VALUE"
        if "add" in command_lower and "filter" in command_lower:
            return self._parse_add_filter(command_lower, current_pipeline)

        # Pattern: "remove NODE_LABEL"
        if "remove" in command_lower or "delete" in command_lower:
            return self._parse_remove(command_lower, current_pipeline)

        # Pattern: "scale NODE to N instances"
        if "scale" in command_lower or "parallel" in command_lower:
            return self._parse_scale(command_lower, current_pipeline)

        # Pattern: "add alert/sink"
        if "add" in command_lower and ("alert" in command_lower or "sink" in command_lower):
            return self._parse_add_sink(command_lower, current_pipeline)

        return {
            "interpretation": f"Could not parse: {command}",
            "actions": [],
            "error": "Command not recognized. Try: 'add a filter where temperature > 30'",
        }

    def _parse_add_filter(self, cmd: str, pipeline: dict) -> dict:
        """Parse 'add a filter where field condition value'."""
        import re

        # Try to extract: field, condition, value
        patterns = [
            r"where\s+(\w+)\s*(?:is\s+)?(>|<|>=|<=|==|!=|above|below|greater|less)\s*(?:than\s+)?(\d+\.?\d*)",
            r"(?:drops?|removes?|filters?)\s+.*?(\w+)\s*(>|<|>=|<=)\s*(\d+\.?\d*)",
            r"(\w+)\s*(above|below|greater than|less than|over|under)\s+(\d+\.?\d*)",
        ]

        condition_map = {
            ">": "gt", "<": "lt", ">=": "gte", "<=": "lte",
            "==": "eq", "!=": "neq",
            "above": "gt", "below": "lt", "over": "gt", "under": "lt",
            "greater": "gt", "less": "lt",
            "greater than": "gt", "less than": "lt",
        }

        for pattern in patterns:
            match = re.search(pattern, cmd)
            if match:
                field = match.group(1)
                condition = condition_map.get(match.group(2), "gt")
                value = float(match.group(3))

                # Find a good insertion point (after first source or first operator)
                nodes = pipeline.get("nodes", [])
                connect_after = None
                for n in nodes:
                    ot = n.get("operator_type", "")
                    if "source" in ot:
                        connect_after = n.get("id")
                        break

                return {
                    "interpretation": f"Add a filter: keep events where {field} {condition} {value}",
                    "actions": [{
                        "action": "add_node",
                        "node": {
                            "label": f"Filter {field} {condition} {value}",
                            "operator_type": "filter",
                            "config": {
                                "field": field,
                                "condition": condition,
                                "value": value,
                            },
                        },
                        "connect_after": connect_after,
                    }],
                }

        return {
            "interpretation": f"Understood: add a filter, but couldn't parse the condition from: {cmd}",
            "actions": [],
            "error": "Try: 'add a filter where temperature > 30'",
        }

    def _parse_remove(self, cmd: str, pipeline: dict) -> dict:
        """Parse 'remove NODE_LABEL'."""
        nodes = pipeline.get("nodes", [])
        for node in nodes:
            label = node.get("label", "").lower()
            if label in cmd:
                return {
                    "interpretation": f"Remove node '{node.get('label')}'",
                    "actions": [{
                        "action": "remove_node",
                        "node_id": node.get("id"),
                        "label": node.get("label"),
                    }],
                }

        return {
            "interpretation": f"Remove a node, but couldn't find which one in: {cmd}",
            "actions": [],
        }

    def _parse_scale(self, cmd: str, pipeline: dict) -> dict:
        """Parse 'scale NODE to N instances'."""
        import re
        match = re.search(r"(\d+)\s*(?:instances|workers|parallel)", cmd)
        target = int(match.group(1)) if match else 3

        return {
            "interpretation": f"Scale an operator to {target} parallel instances",
            "actions": [{
                "action": "scale_node",
                "target_parallelism": target,
            }],
        }

    def _parse_add_sink(self, cmd: str, pipeline: dict) -> dict:
        """Parse 'add an alert sink'."""
        if "alert" in cmd:
            return {
                "interpretation": "Add an alert sink to the pipeline",
                "actions": [{
                    "action": "add_node",
                    "node": {
                        "label": "Alert Sink",
                        "operator_type": "alert_sink",
                        "config": {"alert_channel": "console"},
                    },
                }],
            }

        return {
            "interpretation": "Add a sink to the pipeline",
            "actions": [{
                "action": "add_node",
                "node": {
                    "label": "Console Sink",
                    "operator_type": "console_sink",
                    "config": {},
                },
            }],
        }
