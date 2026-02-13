import { create } from "zustand";
import type { Pipeline, PipelineNode, PipelineEdge, PipelineVersion } from "../types/pipeline";

interface PipelineState {
  pipeline: Pipeline | null;
  versions: PipelineVersion[];
  selectedNodeId: string | null;
  isDirty: boolean;

  setPipeline: (pipeline: Pipeline) => void;
  addNode: (node: PipelineNode) => void;
  removeNode: (nodeId: string) => void;
  updateNode: (nodeId: string, updates: Partial<PipelineNode>) => void;
  addEdge: (edge: PipelineEdge) => void;
  removeEdge: (edgeId: string) => void;
  selectNode: (nodeId: string | null) => void;
  setVersions: (versions: PipelineVersion[]) => void;
  reset: () => void;
}

export const usePipelineStore = create<PipelineState>((set) => ({
  pipeline: null,
  versions: [],
  selectedNodeId: null,
  isDirty: false,

  setPipeline: (pipeline) => set({ pipeline, isDirty: false }),

  addNode: (node) =>
    set((state) => {
      if (!state.pipeline) return state;
      return {
        pipeline: {
          ...state.pipeline,
          nodes: [...state.pipeline.nodes, node],
        },
        isDirty: true,
      };
    }),

  removeNode: (nodeId) =>
    set((state) => {
      if (!state.pipeline) return state;
      return {
        pipeline: {
          ...state.pipeline,
          nodes: state.pipeline.nodes.filter((n) => n.id !== nodeId),
          edges: state.pipeline.edges.filter(
            (e) => e.source_node_id !== nodeId && e.target_node_id !== nodeId
          ),
        },
        selectedNodeId:
          state.selectedNodeId === nodeId ? null : state.selectedNodeId,
        isDirty: true,
      };
    }),

  updateNode: (nodeId, updates) =>
    set((state) => {
      if (!state.pipeline) return state;
      return {
        pipeline: {
          ...state.pipeline,
          nodes: state.pipeline.nodes.map((n) =>
            n.id === nodeId ? { ...n, ...updates } : n
          ),
        },
        isDirty: true,
      };
    }),

  addEdge: (edge) =>
    set((state) => {
      if (!state.pipeline) return state;
      return {
        pipeline: {
          ...state.pipeline,
          edges: [...state.pipeline.edges, edge],
        },
        isDirty: true,
      };
    }),

  removeEdge: (edgeId) =>
    set((state) => {
      if (!state.pipeline) return state;
      return {
        pipeline: {
          ...state.pipeline,
          edges: state.pipeline.edges.filter((e) => e.id !== edgeId),
        },
        isDirty: true,
      };
    }),

  selectNode: (nodeId) => set({ selectedNodeId: nodeId }),

  setVersions: (versions) => set({ versions }),

  reset: () =>
    set({ pipeline: null, versions: [], selectedNodeId: null, isDirty: false }),
}));
