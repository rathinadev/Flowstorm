# FlowStorm API Reference

**Version:** 1.0.0
**Last Updated:** 2026-02-16

## Table of Contents

- [Overview](#overview)
- [Base URL](#base-url)
- [Authentication](#authentication)
- [Response Format](#response-format)
- [Error Handling](#error-handling)
- [Endpoints](#endpoints)
  - [Pipeline Management](#pipeline-management)
  - [Chaos Engineering](#chaos-engineering)
  - [Version Control](#version-control)
  - [Data Lineage](#data-lineage)
  - [Health & Self-Healing](#health--self-healing)
  - [Dead Letter Queue](#dead-letter-queue)
  - [A/B Testing](#ab-testing)
  - [Predictive Scaling](#predictive-scaling)
  - [Demo Mode](#demo-mode)
  - [Health Check](#health-check)
- [WebSocket API](#websocket-api)
- [WebSocket Events Reference](#websocket-events-reference)

---

## Overview

FlowStorm is a distributed stream processing engine that provides real-time data pipeline orchestration with advanced features including chaos engineering, self-healing, version control, and predictive scaling.

This document describes the REST API and WebSocket interfaces for interacting with FlowStorm.

## Base URL

```
http://localhost:3000
```

For production deployments, replace with your production domain.

## Authentication

Currently, FlowStorm API endpoints do not require authentication. For production use, implement appropriate authentication mechanisms (API keys, OAuth, etc.).

## Response Format

All API responses use JSON format. Successful responses return HTTP status codes in the 2xx range. Error responses return 4xx or 5xx status codes with error details.

## Error Handling

Error responses follow this structure:

```json
{
  "error": "Error message describing what went wrong",
  "code": "ERROR_CODE",
  "details": {}
}
```

Common HTTP status codes:
- `200 OK` - Request succeeded
- `201 Created` - Resource created successfully
- `400 Bad Request` - Invalid request parameters
- `404 Not Found` - Resource not found
- `500 Internal Server Error` - Server error

---

## Endpoints

### Pipeline Management

#### Create Pipeline

Creates a new stream processing pipeline.

**Endpoint:** `POST /api/pipelines`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| name | string | Yes | Pipeline name |
| description | string | No | Pipeline description |
| nodes | array | Yes | Array of node definitions |
| edges | array | Yes | Array of edge definitions connecting nodes |

**Node Definition:**

```json
{
  "id": "node_id",
  "type": "source|filter|transform|sink",
  "operator": "operator_name",
  "config": {}
}
```

**Edge Definition:**

```json
{
  "from": "source_node_id",
  "to": "target_node_id"
}
```

**Example Request:**

```json
{
  "name": "User Activity Pipeline",
  "description": "Processes user activity events",
  "nodes": [
    {
      "id": "source1",
      "type": "source",
      "operator": "kafka",
      "config": {
        "topic": "user-events",
        "brokers": ["localhost:9092"]
      }
    },
    {
      "id": "filter1",
      "type": "filter",
      "operator": "condition",
      "config": {
        "condition": "event.type === 'click'"
      }
    },
    {
      "id": "sink1",
      "type": "sink",
      "operator": "elasticsearch",
      "config": {
        "index": "user-clicks"
      }
    }
  ],
  "edges": [
    {"from": "source1", "to": "filter1"},
    {"from": "filter1", "to": "sink1"}
  ]
}
```

**Response:** `201 Created`

```json
{
  "id": "pipe_abc123",
  "name": "User Activity Pipeline",
  "status": "running",
  "nodes": [
    {
      "id": "source1",
      "type": "source",
      "operator": "kafka",
      "config": {
        "topic": "user-events",
        "brokers": ["localhost:9092"]
      }
    }
  ],
  "edges": [
    {"from": "source1", "to": "filter1"}
  ],
  "created_at": "2026-02-16T10:30:00Z"
}
```

**Error Responses:**

- `400 Bad Request` - Invalid pipeline configuration
- `500 Internal Server Error` - Failed to create pipeline

---

#### List All Pipelines

Retrieves all pipelines in the system.

**Endpoint:** `GET /api/pipelines`

**Query Parameters:** None

**Response:** `200 OK`

```json
[
  {
    "id": "pipe_abc123",
    "name": "User Activity Pipeline",
    "status": "running"
  },
  {
    "id": "pipe_def456",
    "name": "Analytics Pipeline",
    "status": "stopped"
  }
]
```

**Error Responses:**

- `500 Internal Server Error` - Failed to retrieve pipelines

---

#### Get Pipeline Status

Retrieves detailed information about a specific pipeline.

**Endpoint:** `GET /api/pipelines/:id`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Pipeline ID |

**Response:** `200 OK`

```json
{
  "id": "pipe_abc123",
  "name": "User Activity Pipeline",
  "status": "running",
  "nodes": [
    {
      "id": "source1",
      "type": "source",
      "operator": "kafka",
      "config": {}
    }
  ],
  "edges": [
    {"from": "source1", "to": "filter1"}
  ],
  "version": "v3",
  "created_at": "2026-02-16T10:30:00Z",
  "updated_at": "2026-02-16T11:15:00Z"
}
```

**Error Responses:**

- `404 Not Found` - Pipeline does not exist
- `500 Internal Server Error` - Failed to retrieve pipeline

---

#### Delete Pipeline

Stops and deletes a pipeline.

**Endpoint:** `DELETE /api/pipelines/:id`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Pipeline ID |

**Response:** `200 OK`

```json
{
  "status": "stopped",
  "message": "Pipeline deleted successfully"
}
```

**Error Responses:**

- `404 Not Found` - Pipeline does not exist
- `500 Internal Server Error` - Failed to delete pipeline

---

### Chaos Engineering

#### Start Chaos Testing

Initiates chaos engineering scenarios on a running pipeline.

**Endpoint:** `POST /api/pipelines/:id/chaos`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Pipeline ID |

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| intensity | string | Yes | Chaos intensity level: "low", "medium", or "high" |
| duration_seconds | integer | Yes | Duration of chaos testing in seconds |

**Example Request:**

```json
{
  "intensity": "medium",
  "duration_seconds": 300
}
```

**Response:** `200 OK`

```json
{
  "status": "active",
  "intensity": "medium",
  "duration_seconds": 300,
  "scenarios": [
    "worker_crash",
    "network_delay",
    "cpu_spike",
    "memory_leak"
  ],
  "started_at": "2026-02-16T12:00:00Z",
  "expected_end": "2026-02-16T12:05:00Z"
}
```

**Error Responses:**

- `400 Bad Request` - Invalid intensity level or duration
- `404 Not Found` - Pipeline does not exist
- `409 Conflict` - Chaos testing already active
- `500 Internal Server Error` - Failed to start chaos testing

---

#### Stop Chaos Testing

Stops ongoing chaos testing on a pipeline.

**Endpoint:** `DELETE /api/pipelines/:id/chaos`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Pipeline ID |

**Response:** `200 OK`

```json
{
  "status": "stopped",
  "message": "Chaos testing stopped",
  "total_events": 47,
  "duration_seconds": 180
}
```

**Error Responses:**

- `404 Not Found` - Pipeline does not exist or no active chaos testing
- `500 Internal Server Error` - Failed to stop chaos testing

---

#### Get Chaos Event History

Retrieves the history of chaos events for a pipeline.

**Endpoint:** `GET /api/pipelines/:id/chaos/history`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Pipeline ID |

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| limit | integer | Maximum number of events to return (default: 100) |

**Response:** `200 OK`

```json
[
  {
    "scenario": "worker_crash",
    "target": "worker_node_filter1_0",
    "severity": "high",
    "timestamp": "2026-02-16T12:02:15Z",
    "details": "Simulated worker crash",
    "recovery_time_ms": 1250
  },
  {
    "scenario": "network_delay",
    "target": "worker_node_source1_1",
    "severity": "medium",
    "timestamp": "2026-02-16T12:01:30Z",
    "details": "Injected 500ms network latency",
    "recovery_time_ms": null
  }
]
```

**Error Responses:**

- `404 Not Found` - Pipeline does not exist
- `500 Internal Server Error` - Failed to retrieve history

---

### Version Control

#### Get Version History

Retrieves version history for a pipeline.

**Endpoint:** `GET /api/pipelines/:id/versions`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Pipeline ID |

**Response:** `200 OK`

```json
[
  {
    "version_id": "v3",
    "trigger": "manual",
    "description": "Added new filter node",
    "timestamp": "2026-02-16T11:15:00Z",
    "node_count": 5,
    "edge_count": 4,
    "author": "system"
  },
  {
    "version_id": "v2",
    "trigger": "auto",
    "description": "Optimizer modified edge weights",
    "timestamp": "2026-02-16T10:45:00Z",
    "node_count": 4,
    "edge_count": 3,
    "author": "optimizer"
  },
  {
    "version_id": "v1",
    "trigger": "creation",
    "description": "Initial pipeline creation",
    "timestamp": "2026-02-16T10:30:00Z",
    "node_count": 4,
    "edge_count": 3,
    "author": "system"
  }
]
```

**Error Responses:**

- `404 Not Found` - Pipeline does not exist
- `500 Internal Server Error` - Failed to retrieve versions

---

#### Compare Versions

Compares two pipeline versions and returns the differences.

**Endpoint:** `GET /api/pipelines/:id/versions/:from/diff/:to`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Pipeline ID |
| from | string | Source version ID |
| to | string | Target version ID |

**Response:** `200 OK`

```json
{
  "version_from": "v2",
  "version_to": "v3",
  "stats": {
    "nodes_added": 1,
    "nodes_removed": 0,
    "nodes_modified": 0,
    "edges_added": 1,
    "edges_removed": 0,
    "edges_modified": 0
  },
  "node_diffs": [
    {
      "type": "added",
      "node": {
        "id": "filter2",
        "type": "filter",
        "operator": "dedup",
        "config": {"window_ms": 5000}
      }
    }
  ],
  "edge_diffs": [
    {
      "type": "added",
      "edge": {
        "from": "filter1",
        "to": "filter2"
      }
    }
  ]
}
```

**Error Responses:**

- `404 Not Found` - Pipeline or version does not exist
- `500 Internal Server Error` - Failed to compute diff

---

#### Rollback Pipeline

Rolls back a pipeline to a previous version.

**Endpoint:** `POST /api/pipelines/:id/rollback`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Pipeline ID |

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| version_id | string | Yes | Target version ID to rollback to |

**Example Request:**

```json
{
  "version_id": "v2"
}
```

**Response:** `200 OK`

```json
{
  "status": "success",
  "rolled_back_to": "v2",
  "new_version": "v4",
  "message": "Pipeline rolled back successfully"
}
```

**Error Responses:**

- `400 Bad Request` - Invalid version ID
- `404 Not Found` - Pipeline or version does not exist
- `500 Internal Server Error` - Rollback failed

---

### Data Lineage

#### Get Event Lineage

Traces the lineage of a specific event through the pipeline.

**Endpoint:** `GET /api/pipelines/:id/lineage/:eventId`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Pipeline ID |
| eventId | string | Event ID to trace |

**Response:** `200 OK`

```json
{
  "event_id": "evt_xyz789",
  "pipeline_id": "pipe_abc123",
  "total_steps": 4,
  "total_processing_time_ms": 45,
  "steps": [
    {
      "node_id": "source1",
      "operator_type": "kafka",
      "timestamp": "2026-02-16T12:30:00.000Z",
      "processing_time_ms": 5,
      "input": null,
      "output": {
        "id": "evt_xyz789",
        "type": "click",
        "user_id": "user123"
      }
    },
    {
      "node_id": "filter1",
      "operator_type": "condition",
      "timestamp": "2026-02-16T12:30:00.010Z",
      "processing_time_ms": 2,
      "input": {
        "id": "evt_xyz789",
        "type": "click",
        "user_id": "user123"
      },
      "output": {
        "id": "evt_xyz789",
        "type": "click",
        "user_id": "user123"
      }
    },
    {
      "node_id": "transform1",
      "operator_type": "map",
      "timestamp": "2026-02-16T12:30:00.015Z",
      "processing_time_ms": 8,
      "input": {
        "id": "evt_xyz789",
        "type": "click",
        "user_id": "user123"
      },
      "output": {
        "id": "evt_xyz789",
        "type": "click",
        "user_id": "user123",
        "enriched": true,
        "timestamp": "2026-02-16T12:30:00.000Z"
      }
    },
    {
      "node_id": "sink1",
      "operator_type": "elasticsearch",
      "timestamp": "2026-02-16T12:30:00.045Z",
      "processing_time_ms": 30,
      "input": {
        "id": "evt_xyz789",
        "type": "click",
        "user_id": "user123",
        "enriched": true,
        "timestamp": "2026-02-16T12:30:00.000Z"
      },
      "output": {
        "indexed": true,
        "document_id": "doc_abc"
      }
    }
  ]
}
```

**Error Responses:**

- `404 Not Found` - Pipeline or event not found
- `500 Internal Server Error` - Failed to retrieve lineage

---

### Health & Self-Healing

#### Get Worker Health

Retrieves health metrics for all workers in a pipeline.

**Endpoint:** `GET /api/pipelines/:id/health`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Pipeline ID |

**Response:** `200 OK`

```json
{
  "pipeline_id": "pipe_abc123",
  "overall_health": "healthy",
  "workers": {
    "worker_node_source1_0": {
      "health_score": 0.95,
      "status": "healthy",
      "metrics": {
        "cpu_percent": 45,
        "memory_mb": 256,
        "events_processed": 15000,
        "error_rate": 0.001,
        "uptime_seconds": 3600
      }
    },
    "worker_node_filter1_0": {
      "health_score": 0.88,
      "status": "healthy",
      "metrics": {
        "cpu_percent": 60,
        "memory_mb": 512,
        "events_processed": 15000,
        "error_rate": 0.005,
        "uptime_seconds": 3600
      }
    },
    "worker_node_sink1_0": {
      "health_score": 0.45,
      "status": "degraded",
      "metrics": {
        "cpu_percent": 85,
        "memory_mb": 1024,
        "events_processed": 14500,
        "error_rate": 0.033,
        "uptime_seconds": 1800
      }
    }
  },
  "timestamp": "2026-02-16T12:45:00Z"
}
```

**Error Responses:**

- `404 Not Found` - Pipeline does not exist
- `500 Internal Server Error` - Failed to retrieve health data

---

#### Get Healing Log

Retrieves self-healing action history for a pipeline.

**Endpoint:** `GET /api/pipelines/:id/healing-log`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Pipeline ID |

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| limit | integer | Maximum number of entries to return (default: 50) |

**Response:** `200 OK`

```json
[
  {
    "action": "restart_worker",
    "trigger": "worker_crash",
    "target_node_id": "filter1",
    "target_worker_id": "worker_node_filter1_0",
    "details": "Worker crashed with exit code 1",
    "events_replayed": 127,
    "duration_ms": 1450,
    "success": true,
    "timestamp": "2026-02-16T12:35:00Z"
  },
  {
    "action": "scale_up",
    "trigger": "high_cpu",
    "target_node_id": "transform1",
    "target_worker_id": null,
    "details": "CPU usage exceeded 80% for 5 minutes",
    "events_replayed": 0,
    "duration_ms": 2300,
    "success": true,
    "timestamp": "2026-02-16T12:20:00Z"
  },
  {
    "action": "replay_events",
    "trigger": "data_loss_detection",
    "target_node_id": "sink1",
    "target_worker_id": "worker_node_sink1_1",
    "details": "Detected 50 missing events in sink",
    "events_replayed": 50,
    "duration_ms": 890,
    "success": true,
    "timestamp": "2026-02-16T11:55:00Z"
  }
]
```

**Error Responses:**

- `404 Not Found` - Pipeline does not exist
- `500 Internal Server Error` - Failed to retrieve healing log

---

### Dead Letter Queue

#### Get Dead Letter Queue Entries

Retrieves failed events from the Dead Letter Queue.

**Endpoint:** `GET /api/pipelines/:id/dlq`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Pipeline ID |

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| count | integer | Maximum number of entries to return (default: 50) |
| offset | integer | Offset for pagination (default: 0) |

**Response:** `200 OK`

```json
[
  {
    "event_id": "evt_fail_001",
    "node_id": "transform1",
    "failure_type": "transformation_error",
    "error_message": "TypeError: Cannot read property 'value' of undefined",
    "suggestion": "Check if input event has required 'value' field",
    "original_event": {
      "id": "evt_abc",
      "type": "click",
      "data": {}
    },
    "timestamp": "2026-02-16T13:10:00Z",
    "retry_count": 3
  },
  {
    "event_id": "evt_fail_002",
    "node_id": "sink1",
    "failure_type": "sink_error",
    "error_message": "Connection timeout to Elasticsearch",
    "suggestion": "Verify Elasticsearch is reachable and not overloaded",
    "original_event": {
      "id": "evt_def",
      "type": "impression",
      "user_id": "user456"
    },
    "timestamp": "2026-02-16T13:08:00Z",
    "retry_count": 5
  }
]
```

**Error Responses:**

- `404 Not Found` - Pipeline does not exist
- `500 Internal Server Error` - Failed to retrieve DLQ entries

---

#### Get Dead Letter Queue Statistics

Retrieves statistics about failures in the Dead Letter Queue.

**Endpoint:** `GET /api/pipelines/:id/dlq/stats`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Pipeline ID |

**Response:** `200 OK`

```json
{
  "pipeline_id": "pipe_abc123",
  "total_failures": 247,
  "by_type": {
    "transformation_error": 120,
    "sink_error": 85,
    "validation_error": 42
  },
  "by_node": {
    "transform1": 120,
    "sink1": 85,
    "filter1": 42
  },
  "failure_rate": 0.0164,
  "time_window": "last_24h",
  "timestamp": "2026-02-16T13:15:00Z"
}
```

**Error Responses:**

- `404 Not Found` - Pipeline does not exist
- `500 Internal Server Error` - Failed to retrieve statistics

---

### A/B Testing

#### Create A/B Test

Creates a new A/B test between two pipelines.

**Endpoint:** `POST /api/ab-tests`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| pipeline_id_a | string | Yes | ID of pipeline A |
| pipeline_id_b | string | Yes | ID of pipeline B |
| split_percentage | integer | Yes | Percentage of traffic to pipeline A (0-100) |
| name | string | Yes | Test name |
| description | string | No | Test description |

**Example Request:**

```json
{
  "pipeline_id_a": "pipe_abc123",
  "pipeline_id_b": "pipe_def456",
  "split_percentage": 50,
  "name": "New Filter Algorithm Test",
  "description": "Testing improved filtering algorithm in pipeline B"
}
```

**Response:** `201 Created`

```json
{
  "test_id": "test_xyz789",
  "name": "New Filter Algorithm Test",
  "pipeline_id_a": "pipe_abc123",
  "pipeline_id_b": "pipe_def456",
  "split_percentage": 50,
  "status": "running",
  "created_at": "2026-02-16T13:30:00Z"
}
```

**Error Responses:**

- `400 Bad Request` - Invalid parameters
- `404 Not Found` - One or both pipelines do not exist
- `500 Internal Server Error` - Failed to create test

---

#### List A/B Tests

Retrieves all A/B tests.

**Endpoint:** `GET /api/ab-tests`

**Response:** `200 OK`

```json
[
  {
    "test_id": "test_xyz789",
    "name": "New Filter Algorithm Test",
    "pipeline_id_a": "pipe_abc123",
    "pipeline_id_b": "pipe_def456",
    "split_percentage": 50,
    "status": "running",
    "created_at": "2026-02-16T13:30:00Z"
  },
  {
    "test_id": "test_old123",
    "name": "Transform Performance Test",
    "pipeline_id_a": "pipe_aaa111",
    "pipeline_id_b": "pipe_bbb222",
    "split_percentage": 25,
    "status": "completed",
    "created_at": "2026-02-15T09:00:00Z"
  }
]
```

**Error Responses:**

- `500 Internal Server Error` - Failed to retrieve tests

---

#### Get A/B Test Results

Retrieves detailed results and metrics comparison for an A/B test.

**Endpoint:** `GET /api/ab-tests/:testId`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| testId | string | A/B test ID |

**Response:** `200 OK`

```json
{
  "test_id": "test_xyz789",
  "name": "New Filter Algorithm Test",
  "status": "running",
  "duration_seconds": 7200,
  "pipeline_a": {
    "pipeline_id": "pipe_abc123",
    "events_processed": 500000,
    "avg_latency_ms": 45,
    "p95_latency_ms": 120,
    "p99_latency_ms": 250,
    "error_rate": 0.0012,
    "throughput_per_sec": 694
  },
  "pipeline_b": {
    "pipeline_id": "pipe_def456",
    "events_processed": 500000,
    "avg_latency_ms": 38,
    "p95_latency_ms": 95,
    "p99_latency_ms": 180,
    "error_rate": 0.0008,
    "throughput_per_sec": 694
  },
  "comparison": {
    "latency_improvement": "15.6%",
    "error_rate_improvement": "33.3%",
    "throughput_difference": "0%",
    "statistical_significance": 0.98,
    "recommendation": "pipeline_b"
  },
  "created_at": "2026-02-16T13:30:00Z"
}
```

**Error Responses:**

- `404 Not Found` - Test does not exist
- `500 Internal Server Error` - Failed to retrieve results

---

#### Stop A/B Test

Stops a running A/B test.

**Endpoint:** `DELETE /api/ab-tests/:testId`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| testId | string | A/B test ID |

**Response:** `200 OK`

```json
{
  "status": "stopped",
  "test_id": "test_xyz789",
  "message": "A/B test stopped successfully",
  "final_stats": {
    "duration_seconds": 7200,
    "total_events": 1000000
  }
}
```

**Error Responses:**

- `404 Not Found` - Test does not exist
- `500 Internal Server Error` - Failed to stop test

---

### Predictive Scaling

#### Get Scaling Prediction

Retrieves predictive scaling recommendations for a pipeline.

**Endpoint:** `GET /api/pipelines/:id/prediction`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Pipeline ID |

**Response:** `200 OK`

```json
{
  "pipeline_id": "pipe_abc123",
  "predicted_throughput": 1250,
  "current_throughput": 950,
  "confidence": 0.87,
  "recommendation": "scale_up",
  "reason": "Traffic expected to increase 30% in next 15 minutes based on historical patterns",
  "suggested_workers": {
    "transform1": 4,
    "sink1": 3
  },
  "current_workers": {
    "transform1": 2,
    "sink1": 2
  },
  "prediction_window": "15_minutes",
  "timestamp": "2026-02-16T14:00:00Z"
}
```

**Error Responses:**

- `404 Not Found` - Pipeline does not exist
- `500 Internal Server Error` - Failed to generate prediction

---

### Demo Mode

#### Start Demo Simulator

Starts the demo event simulator.

**Endpoint:** `POST /api/demo/start`

**Request Body:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| rate | integer | No | Events per second (default: 100) |
| event_types | array | No | Event types to generate |

**Example Request:**

```json
{
  "rate": 150,
  "event_types": ["click", "impression", "conversion"]
}
```

**Response:** `200 OK`

```json
{
  "status": "running",
  "rate": 150,
  "message": "Demo simulator started"
}
```

**Error Responses:**

- `409 Conflict` - Simulator already running
- `500 Internal Server Error` - Failed to start simulator

---

#### Stop Demo Simulator

Stops the demo event simulator.

**Endpoint:** `POST /api/demo/stop`

**Response:** `200 OK`

```json
{
  "status": "stopped",
  "message": "Demo simulator stopped",
  "total_events_generated": 45000
}
```

**Error Responses:**

- `404 Not Found` - Simulator not running
- `500 Internal Server Error` - Failed to stop simulator

---

#### Get Demo Status

Retrieves the current status of the demo simulator.

**Endpoint:** `GET /api/demo/status`

**Response:** `200 OK`

```json
{
  "status": "running",
  "rate": 150,
  "events_generated": 12500,
  "uptime_seconds": 83,
  "chaos_active": true
}
```

**Error Responses:**

- `500 Internal Server Error` - Failed to retrieve status

---

#### Toggle Demo Chaos

Enables or disables chaos mode in the demo simulator.

**Endpoint:** `POST /api/demo/chaos`

**Query Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| active | boolean | Enable (true) or disable (false) chaos |

**Example:** `POST /api/demo/chaos?active=true`

**Response:** `200 OK`

```json
{
  "chaos_active": true,
  "message": "Demo chaos enabled"
}
```

**Error Responses:**

- `400 Bad Request` - Invalid active parameter
- `500 Internal Server Error` - Failed to toggle chaos

---

### Health Check

#### Server Health Check

Checks if the FlowStorm server is healthy and responding.

**Endpoint:** `GET /health`

**Response:** `200 OK`

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 86400,
  "timestamp": "2026-02-16T14:30:00Z"
}
```

**Error Responses:**

- `503 Service Unavailable` - Server is unhealthy

---

## WebSocket API

FlowStorm provides a WebSocket interface for real-time pipeline event streaming.

### Connection

**Endpoint:** `WS /api/ws/pipeline/:id`

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| id | string | Pipeline ID to subscribe to |

**Connection Example:**

```javascript
const ws = new WebSocket('ws://localhost:3000/api/ws/pipeline/pipe_abc123');

ws.onopen = () => {
  console.log('Connected to pipeline stream');
};

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received event:', data);
};

ws.onerror = (error) => {
  console.error('WebSocket error:', error);
};

ws.onclose = () => {
  console.log('Disconnected from pipeline stream');
};
```

### Heartbeat

The server sends periodic ping messages to keep the connection alive. Clients should respond with a pong.

**Server Ping:**
```json
{"type": "ping"}
```

**Client Response:**
```json
{"type": "pong"}
```

---

## WebSocket Events Reference

All WebSocket messages follow this structure:

```json
{
  "type": "event_type",
  "timestamp": "2026-02-16T14:45:00Z",
  "data": {}
}
```

### Pipeline Events

#### pipeline.metrics

Real-time pipeline performance metrics.

```json
{
  "type": "pipeline.metrics",
  "timestamp": "2026-02-16T14:45:00Z",
  "data": {
    "pipeline_id": "pipe_abc123",
    "throughput": 1050,
    "latency_p50": 25,
    "latency_p95": 85,
    "latency_p99": 150,
    "error_rate": 0.0015,
    "total_events": 3780000,
    "worker_count": 8
  }
}
```

#### pipeline.deployed

Emitted when a pipeline is successfully deployed.

```json
{
  "type": "pipeline.deployed",
  "timestamp": "2026-02-16T14:45:00Z",
  "data": {
    "pipeline_id": "pipe_abc123",
    "name": "User Activity Pipeline",
    "version": "v1",
    "node_count": 5,
    "edge_count": 4
  }
}
```

#### pipeline.stopped

Emitted when a pipeline is stopped.

```json
{
  "type": "pipeline.stopped",
  "timestamp": "2026-02-16T14:45:00Z",
  "data": {
    "pipeline_id": "pipe_abc123",
    "name": "User Activity Pipeline",
    "reason": "user_requested",
    "total_events_processed": 5000000
  }
}
```

### Worker Events

#### worker.spawned

Emitted when a new worker is spawned.

```json
{
  "type": "worker.spawned",
  "timestamp": "2026-02-16T14:45:00Z",
  "data": {
    "worker_id": "worker_node_transform1_2",
    "node_id": "transform1",
    "pipeline_id": "pipe_abc123",
    "reason": "scale_up"
  }
}
```

#### worker.died

Emitted when a worker terminates unexpectedly.

```json
{
  "type": "worker.died",
  "timestamp": "2026-02-16T14:45:00Z",
  "data": {
    "worker_id": "worker_node_filter1_0",
    "node_id": "filter1",
    "pipeline_id": "pipe_abc123",
    "exit_code": 1,
    "error": "Segmentation fault",
    "uptime_seconds": 3600
  }
}
```

#### worker.recovered

Emitted when a worker is successfully recovered after failure.

```json
{
  "type": "worker.recovered",
  "timestamp": "2026-02-16T14:45:00Z",
  "data": {
    "worker_id": "worker_node_filter1_0",
    "node_id": "filter1",
    "pipeline_id": "pipe_abc123",
    "recovery_time_ms": 1450,
    "events_replayed": 127
  }
}
```

#### worker.scaled

Emitted when workers are scaled up or down.

```json
{
  "type": "worker.scaled",
  "timestamp": "2026-02-16T14:45:00Z",
  "data": {
    "node_id": "transform1",
    "pipeline_id": "pipe_abc123",
    "direction": "up",
    "previous_count": 2,
    "new_count": 4,
    "reason": "high_cpu",
    "trigger": "auto"
  }
}
```

#### worker.stopped

Emitted when a worker is intentionally stopped.

```json
{
  "type": "worker.stopped",
  "timestamp": "2026-02-16T14:45:00Z",
  "data": {
    "worker_id": "worker_node_sink1_1",
    "node_id": "sink1",
    "pipeline_id": "pipe_abc123",
    "reason": "scale_down",
    "events_processed": 150000
  }
}
```

### Optimizer Events

#### optimizer.applied

Emitted when the optimizer applies changes to a pipeline.

```json
{
  "type": "optimizer.applied",
  "timestamp": "2026-02-16T14:45:00Z",
  "data": {
    "pipeline_id": "pipe_abc123",
    "optimization_type": "load_balancing",
    "changes": {
      "edges_modified": 2,
      "weights_updated": true
    },
    "expected_improvement": "15% latency reduction",
    "new_version": "v5"
  }
}
```

### Chaos Events

#### chaos.started

Emitted when chaos testing begins.

```json
{
  "type": "chaos.started",
  "timestamp": "2026-02-16T14:45:00Z",
  "data": {
    "pipeline_id": "pipe_abc123",
    "intensity": "medium",
    "duration_seconds": 300,
    "scenarios": ["worker_crash", "network_delay", "cpu_spike"]
  }
}
```

#### chaos.event

Emitted for each chaos event during testing.

```json
{
  "type": "chaos.event",
  "timestamp": "2026-02-16T14:45:00Z",
  "data": {
    "pipeline_id": "pipe_abc123",
    "scenario": "worker_crash",
    "target": "worker_node_filter1_0",
    "severity": "high",
    "details": "Simulated worker crash"
  }
}
```

#### chaos.stopped

Emitted when chaos testing ends.

```json
{
  "type": "chaos.stopped",
  "timestamp": "2026-02-16T14:45:00Z",
  "data": {
    "pipeline_id": "pipe_abc123",
    "total_events": 47,
    "duration_seconds": 300,
    "summary": {
      "worker_crashes": 12,
      "network_delays": 15,
      "cpu_spikes": 10,
      "memory_leaks": 10
    }
  }
}
```

### Version Control Events

#### pipeline_git.version

Emitted when a new pipeline version is created.

```json
{
  "type": "pipeline_git.version",
  "timestamp": "2026-02-16T14:45:00Z",
  "data": {
    "pipeline_id": "pipe_abc123",
    "version_id": "v6",
    "trigger": "manual",
    "description": "Added deduplication filter",
    "author": "system",
    "changes": {
      "nodes_added": 1,
      "edges_added": 2
    }
  }
}
```

### Connection Events

#### subscribed

Emitted when client successfully subscribes to a pipeline stream.

```json
{
  "type": "subscribed",
  "timestamp": "2026-02-16T14:45:00Z",
  "data": {
    "pipeline_id": "pipe_abc123",
    "message": "Successfully subscribed to pipeline events"
  }
}
```

#### pong

Response to server's ping heartbeat.

```json
{
  "type": "pong",
  "timestamp": "2026-02-16T14:45:00Z"
}
```

---

## Rate Limiting

Currently, FlowStorm does not implement rate limiting. For production deployments, consider implementing rate limiting at the API gateway or load balancer level.

## CORS

The FlowStorm API supports Cross-Origin Resource Sharing (CORS) with wildcard origins enabled. For production, configure specific allowed origins.

## Data Retention

- **DLQ Entries:** Retained for 7 days by default
- **Chaos Event History:** Retained for 30 days by default
- **Healing Logs:** Retained for 30 days by default
- **Pipeline Versions:** Retained indefinitely (consider implementing version pruning for production)
- **Metrics:** Real-time only, use external monitoring for historical metrics

## Best Practices

1. Always check pipeline status before performing operations
2. Use WebSocket connections for real-time monitoring instead of polling REST endpoints
3. Implement exponential backoff for retrying failed requests
4. Monitor DLQ regularly to identify systemic issues
5. Use A/B testing before deploying major pipeline changes to production
6. Enable chaos testing in staging environments before production rollout
7. Review healing logs to understand system resilience patterns
8. Leverage version control for safe pipeline modifications and rollbacks

---

## Support

For issues, questions, or feature requests, please visit the FlowStorm GitHub repository or contact the development team.

**Version:** 1.0.0
**Last Updated:** 2026-02-16
