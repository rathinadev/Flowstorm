import { create } from "zustand";
import type { ChaosEvent } from "../types/metrics";

interface ChaosState {
  active: boolean;
  intensity: string;
  events: ChaosEvent[];

  setActive: (active: boolean, intensity?: string) => void;
  addEvent: (event: ChaosEvent) => void;
  reset: () => void;
}

export const useChaosStore = create<ChaosState>((set) => ({
  active: false,
  intensity: "medium",
  events: [],

  setActive: (active, intensity) =>
    set((state) => ({
      active,
      intensity: intensity || state.intensity,
    })),

  addEvent: (event) =>
    set((state) => ({
      events: [event, ...state.events].slice(0, 200),
    })),

  reset: () => set({ active: false, intensity: "medium", events: [] }),
}));
