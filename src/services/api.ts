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

  // NLP
  sendNLPCommand(id: string, text: string) {
    return request(`/pipelines/${id}/nlp`, {
      method: "POST",
      body: JSON.stringify({ text }),
    });
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
