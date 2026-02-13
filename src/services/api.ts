const API_BASE = "/api";

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "API request failed");
  }
  return res.json();
}

// Pipeline CRUD
export const api = {
  createPipeline(data: {
    name: string;
    description?: string;
    nodes: Array<{
      id?: string;
      label: string;
      operator_type: string;
      config: Record<string, unknown>;
      position_x: number;
      position_y: number;
    }>;
    edges: Array<{ source_node_id: string; target_node_id: string }>;
  }) {
    return request("/pipelines", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  listPipelines() {
    return request("/pipelines");
  },

  getPipeline(id: string) {
    return request(`/pipelines/${id}`);
  },

  deletePipeline(id: string) {
    return request(`/pipelines/${id}`, { method: "DELETE" });
  },

  // Chaos
  startChaos(id: string, intensity = "medium", durationSeconds = 60) {
    return request(`/pipelines/${id}/chaos`, {
      method: "POST",
      body: JSON.stringify({
        intensity,
        duration_seconds: durationSeconds,
      }),
    });
  },

  stopChaos(id: string) {
    return request(`/pipelines/${id}/chaos`, { method: "DELETE" });
  },

  getChaosHistory(id: string) {
    return request<{ events: Array<Record<string, unknown>> }>(
      `/pipelines/${id}/chaos/history`
    );
  },

  // Pipeline Git
  getVersions(id: string) {
    return request<
      Array<{
        version_id: number;
        trigger: string;
        description: string;
        timestamp: string;
        node_count: number;
        edge_count: number;
      }>
    >(`/pipelines/${id}/versions`);
  },

  diffVersions(id: string, from: number, to: number) {
    return request(`/pipelines/${id}/versions/${from}/diff/${to}`);
  },

  rollback(id: string, versionId: number) {
    return request(`/pipelines/${id}/rollback`, {
      method: "POST",
      body: JSON.stringify({ version_id: versionId }),
    });
  },

  // Lineage
  getLineage(pipelineId: string, eventId: string) {
    return request(`/pipelines/${pipelineId}/lineage/${eventId}`);
  },

  // Health
  getHealth(id: string) {
    return request(`/pipelines/${id}/health`);
  },

  getHealingLog(id: string) {
    return request<{ events: Array<Record<string, unknown>> }>(
      `/pipelines/${id}/healing-log`
    );
  },

  // Dead Letter Queue
  getDLQ(id: string, count = 100) {
    return request<{
      entries: Array<{
        event_id: string;
        node_id: string;
        error_message: string;
        failure_type: string;
        suggestions: string[];
        event_data: Record<string, unknown>;
        timestamp: string;
      }>;
      total: number;
    }>(`/pipelines/${id}/dlq?count=${count}`);
  },

  getDLQStats(id: string) {
    return request<{
      pipeline_id: string;
      total_failed: number;
      groups: Array<{
        failure_type: string;
        count: number;
        affected_nodes: string[];
        suggestions: string[];
      }>;
      by_node: Record<string, number>;
    }>(`/pipelines/${id}/dlq/stats`);
  },

  // A/B Testing
  createABTest(pipelineIdA: string, pipelineIdB: string, splitPercent = 50, name = "") {
    return request(`/ab-tests?pipeline_id_a=${pipelineIdA}&pipeline_id_b=${pipelineIdB}&split_percent=${splitPercent}&name=${encodeURIComponent(name)}`, {
      method: "POST",
    });
  },

  listABTests() {
    return request<{ tests: Array<Record<string, unknown>> }>("/ab-tests");
  },

  getABTest(testId: string) {
    return request(`/ab-tests/${testId}`);
  },

  stopABTest(testId: string) {
    return request(`/ab-tests/${testId}`, { method: "DELETE" });
  },

  // Predictive Scaling
  getPrediction(id: string) {
    return request<{
      predicted_eps: number;
      current_eps: number;
      trend: string;
      confidence: string;
      recommendation: { action: string; reason: string; scale_factor?: number };
    }>(`/pipelines/${id}/prediction`);
  },

  // Demo Mode
  startDemo() {
    return request<{
      pipeline_id: string;
      name: string;
      status: string;
      nodes: Array<{
        id: string;
        label: string;
        operator_type: string;
        node_type: string;
      }>;
      edges: Array<{ source: string; target: string }>;
      workers: number;
    }>("/demo/start", { method: "POST" });
  },

  stopDemo() {
    return request("/demo/stop", { method: "POST" });
  },

  getDemoStatus() {
    return request<{ status: string; pipeline_id?: string }>("/demo/status");
  },

  toggleDemoChaos(active: boolean) {
    return request(`/demo/chaos?active=${active}`, { method: "POST" });
  },

  // Server health
  healthCheck() {
    return request<{
      status: string;
      engine: string;
      version: string;
      active_pipelines: number;
    }>("/health".replace("/api", ""));
  },
};
