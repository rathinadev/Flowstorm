import { describe, it, expect } from "vitest";
import {
  getNodeType,
  OPERATOR_LABELS,
  NODE_COLORS,
  type OperatorType,
} from "../src/types/pipeline";
import { getHealthStatus, HEALTH_COLORS } from "../src/types/metrics";

describe("getNodeType", () => {
  it("should classify source operators", () => {
    expect(getNodeType("mqtt_source")).toBe("source");
    expect(getNodeType("http_source")).toBe("source");
    expect(getNodeType("simulator_source")).toBe("source");
  });

  it("should classify operator types", () => {
    expect(getNodeType("filter")).toBe("operator");
    expect(getNodeType("map")).toBe("operator");
    expect(getNodeType("window")).toBe("operator");
    expect(getNodeType("join")).toBe("operator");
    expect(getNodeType("aggregate")).toBe("operator");
  });

  it("should classify sink operators", () => {
    expect(getNodeType("console_sink")).toBe("sink");
    expect(getNodeType("redis_sink")).toBe("sink");
    expect(getNodeType("alert_sink")).toBe("sink");
    expect(getNodeType("webhook_sink")).toBe("sink");
  });
});

describe("OPERATOR_LABELS", () => {
  it("should have labels for all operator types", () => {
    const allTypes: OperatorType[] = [
      "mqtt_source", "http_source", "simulator_source",
      "filter", "map", "window", "join", "aggregate",
      "console_sink", "redis_sink", "alert_sink", "webhook_sink",
    ];
    for (const t of allTypes) {
      expect(OPERATOR_LABELS[t]).toBeDefined();
      expect(typeof OPERATOR_LABELS[t]).toBe("string");
    }
  });
});

describe("NODE_COLORS", () => {
  it("should have colors for all node types", () => {
    expect(NODE_COLORS.source).toBeDefined();
    expect(NODE_COLORS.operator).toBeDefined();
    expect(NODE_COLORS.sink).toBeDefined();
  });

  it("should return valid hex colors", () => {
    expect(NODE_COLORS.source).toMatch(/^#[0-9a-f]{6}$/);
    expect(NODE_COLORS.operator).toMatch(/^#[0-9a-f]{6}$/);
    expect(NODE_COLORS.sink).toMatch(/^#[0-9a-f]{6}$/);
  });
});

describe("getHealthStatus", () => {
  it("should return healthy for score >= 70", () => {
    expect(getHealthStatus(70)).toBe("healthy");
    expect(getHealthStatus(100)).toBe("healthy");
    expect(getHealthStatus(85)).toBe("healthy");
  });

  it("should return degraded for 30 <= score < 70", () => {
    expect(getHealthStatus(30)).toBe("degraded");
    expect(getHealthStatus(50)).toBe("degraded");
    expect(getHealthStatus(69)).toBe("degraded");
  });

  it("should return critical for 0 < score < 30", () => {
    expect(getHealthStatus(29)).toBe("critical");
    expect(getHealthStatus(1)).toBe("critical");
    expect(getHealthStatus(15)).toBe("critical");
  });

  it("should return dead for score 0", () => {
    expect(getHealthStatus(0)).toBe("dead");
  });
});

describe("HEALTH_COLORS", () => {
  it("should have colors for all statuses", () => {
    expect(HEALTH_COLORS.healthy).toBeDefined();
    expect(HEALTH_COLORS.degraded).toBeDefined();
    expect(HEALTH_COLORS.critical).toBeDefined();
    expect(HEALTH_COLORS.dead).toBeDefined();
  });
});
