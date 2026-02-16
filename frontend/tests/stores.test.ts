import { describe, it, expect, beforeEach } from "vitest";
import { usePipelineStore } from "../src/store/pipelineStore";
import { useMetricsStore } from "../src/store/metricsStore";
import { useChaosStore } from "../src/store/chaosStore";
import type { Pipeline, PipelineNode, PipelineEdge } from "../src/types/pipeline";
import type { PipelineMetrics, HealingEvent, ChaosEvent } from "../src/types/metrics";

// ---- Pipeline Store ----

function makePipeline(): Pipeline {
  return {
    id: "test-1",
    name: "Test Pipeline",
    description: "",
    nodes: [
      {
        id: "n1",
        label: "Source",
        operator_type: "mqtt_source",
        node_type: "source",
        config: {},
        position_x: 0,
        position_y: 0,
        parallelism: 1,
      },
      {
        id: "n2",
        label: "Filter",
        operator_type: "filter",
        node_type: "operator",
        config: { field: "temperature", condition: "gt", value: 30 },
        position_x: 200,
        position_y: 0,
        parallelism: 1,
      },
    ],
    edges: [
      { id: "e1", source_node_id: "n1", target_node_id: "n2" },
    ],
    status: "draft",
    version: 1,
  };
}

describe("PipelineStore", () => {
  beforeEach(() => {
    usePipelineStore.getState().reset();
  });

  it("should start with null pipeline", () => {
    const state = usePipelineStore.getState();
    expect(state.pipeline).toBeNull();
    expect(state.isDirty).toBe(false);
  });

  it("should set a pipeline", () => {
    const pipeline = makePipeline();
    usePipelineStore.getState().setPipeline(pipeline);

    const state = usePipelineStore.getState();
    expect(state.pipeline).toEqual(pipeline);
    expect(state.pipeline!.nodes).toHaveLength(2);
    expect(state.isDirty).toBe(false);
  });

  it("should add a node and mark dirty", () => {
    usePipelineStore.getState().setPipeline(makePipeline());

    const newNode: PipelineNode = {
      id: "n3",
      label: "Sink",
      operator_type: "console_sink",
      node_type: "sink",
      config: {},
      position_x: 400,
      position_y: 0,
      parallelism: 1,
    };
    usePipelineStore.getState().addNode(newNode);

    const state = usePipelineStore.getState();
    expect(state.pipeline!.nodes).toHaveLength(3);
    expect(state.isDirty).toBe(true);
  });

  it("should remove a node and its edges", () => {
    usePipelineStore.getState().setPipeline(makePipeline());
    usePipelineStore.getState().removeNode("n2");

    const state = usePipelineStore.getState();
    expect(state.pipeline!.nodes).toHaveLength(1);
    expect(state.pipeline!.edges).toHaveLength(0); // edge n1->n2 removed
    expect(state.isDirty).toBe(true);
  });

  it("should update a node", () => {
    usePipelineStore.getState().setPipeline(makePipeline());
    usePipelineStore.getState().updateNode("n2", { label: "Updated Filter" });

    const node = usePipelineStore.getState().pipeline!.nodes.find((n) => n.id === "n2");
    expect(node!.label).toBe("Updated Filter");
  });

  it("should add an edge", () => {
    usePipelineStore.getState().setPipeline(makePipeline());

    const edge: PipelineEdge = {
      id: "e2",
      source_node_id: "n2",
      target_node_id: "n1",
    };
    usePipelineStore.getState().addEdge(edge);
    expect(usePipelineStore.getState().pipeline!.edges).toHaveLength(2);
  });

  it("should remove an edge", () => {
    usePipelineStore.getState().setPipeline(makePipeline());
    usePipelineStore.getState().removeEdge("e1");
    expect(usePipelineStore.getState().pipeline!.edges).toHaveLength(0);
  });

  it("should select and deselect a node", () => {
    usePipelineStore.getState().selectNode("n1");
    expect(usePipelineStore.getState().selectedNodeId).toBe("n1");

    usePipelineStore.getState().selectNode(null);
    expect(usePipelineStore.getState().selectedNodeId).toBeNull();
  });

  it("should clear selected node when that node is removed", () => {
    usePipelineStore.getState().setPipeline(makePipeline());
    usePipelineStore.getState().selectNode("n2");
    usePipelineStore.getState().removeNode("n2");
    expect(usePipelineStore.getState().selectedNodeId).toBeNull();
  });

  it("should reset to initial state", () => {
    usePipelineStore.getState().setPipeline(makePipeline());
    usePipelineStore.getState().selectNode("n1");
    usePipelineStore.getState().reset();

    const state = usePipelineStore.getState();
    expect(state.pipeline).toBeNull();
    expect(state.selectedNodeId).toBeNull();
    expect(state.isDirty).toBe(false);
    expect(state.versions).toHaveLength(0);
  });

  it("should not mutate when pipeline is null", () => {
    usePipelineStore.getState().addNode({
      id: "x",
      label: "X",
      operator_type: "filter",
      node_type: "operator",
      config: {},
      position_x: 0,
      position_y: 0,
      parallelism: 1,
    });
    expect(usePipelineStore.getState().pipeline).toBeNull();
  });
});

// ---- Metrics Store ----

describe("MetricsStore", () => {
  beforeEach(() => {
    useMetricsStore.getState().reset();
  });

  it("should start with null metrics", () => {
    expect(useMetricsStore.getState().metrics).toBeNull();
    expect(useMetricsStore.getState().healingLog).toHaveLength(0);
  });

  it("should set metrics and build throughput history", () => {
    const metrics: PipelineMetrics = {
      workers: {},
      total_events_per_second: 500,
      total_events_processed: 10000,
      active_workers: 3,
    };

    useMetricsStore.getState().setMetrics(metrics);
    const state = useMetricsStore.getState();
    expect(state.metrics).toEqual(metrics);
    expect(state.throughputHistory).toHaveLength(1);
    expect(state.throughputHistory[0].eps).toBe(500);
  });

  it("should cap throughput history at 61 samples", () => {
    const metrics: PipelineMetrics = {
      workers: {},
      total_events_per_second: 100,
      total_events_processed: 1000,
      active_workers: 1,
    };

    for (let i = 0; i < 70; i++) {
      useMetricsStore.getState().setMetrics({ ...metrics, total_events_per_second: i });
    }

    expect(useMetricsStore.getState().throughputHistory.length).toBeLessThanOrEqual(61);
  });

  it("should add healing events (newest first)", () => {
    const event1: HealingEvent = {
      action: "failover",
      trigger: "Worker died",
      target_node_id: "n1",
      details: "Recovered",
      events_replayed: 100,
      duration_ms: 500,
      success: true,
      timestamp: "2024-01-01T00:00:00Z",
    };
    const event2: HealingEvent = {
      ...event1,
      action: "scale_out",
      timestamp: "2024-01-01T00:01:00Z",
    };

    useMetricsStore.getState().addHealingEvent(event1);
    useMetricsStore.getState().addHealingEvent(event2);

    const log = useMetricsStore.getState().healingLog;
    expect(log).toHaveLength(2);
    expect(log[0].action).toBe("scale_out"); // newest first
  });

  it("should cap healing log at 100 entries", () => {
    const event: HealingEvent = {
      action: "restart",
      trigger: "Test",
      target_node_id: "n1",
      details: "",
      events_replayed: 0,
      duration_ms: 0,
      success: true,
      timestamp: "2024-01-01T00:00:00Z",
    };

    for (let i = 0; i < 120; i++) {
      useMetricsStore.getState().addHealingEvent(event);
    }

    expect(useMetricsStore.getState().healingLog).toHaveLength(100);
  });
});

// ---- Chaos Store ----

describe("ChaosStore", () => {
  beforeEach(() => {
    useChaosStore.getState().reset();
  });

  it("should start inactive", () => {
    const state = useChaosStore.getState();
    expect(state.active).toBe(false);
    expect(state.events).toHaveLength(0);
  });

  it("should activate and deactivate", () => {
    useChaosStore.getState().setActive(true, "high");
    expect(useChaosStore.getState().active).toBe(true);
    expect(useChaosStore.getState().intensity).toBe("high");

    useChaosStore.getState().setActive(false);
    expect(useChaosStore.getState().active).toBe(false);
    expect(useChaosStore.getState().intensity).toBe("high"); // preserved
  });

  it("should add events (newest first, capped at 200)", () => {
    const event: ChaosEvent = {
      scenario: "kill_worker",
      target: "w1",
      description: "Killed worker w1",
      severity: "high",
      timestamp: "2024-01-01T00:00:00Z",
    };

    for (let i = 0; i < 210; i++) {
      useChaosStore.getState().addEvent({ ...event, target: `w${i}` });
    }

    const events = useChaosStore.getState().events;
    expect(events).toHaveLength(200);
    expect(events[0].target).toBe("w209"); // newest first
  });

  it("should reset to initial state", () => {
    useChaosStore.getState().setActive(true, "high");
    useChaosStore.getState().addEvent({
      scenario: "test",
      target: "w1",
      description: "Test",
      severity: "low",
      timestamp: "2024-01-01T00:00:00Z",
    });

    useChaosStore.getState().reset();
    const state = useChaosStore.getState();
    expect(state.active).toBe(false);
    expect(state.events).toHaveLength(0);
    expect(state.intensity).toBe("medium");
  });
});
