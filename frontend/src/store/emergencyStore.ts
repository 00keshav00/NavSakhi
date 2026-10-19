import { create } from "zustand";

// 1. We define the "shape" of our memory (TypeScript Interface)
interface EmergencyState {
  isSOSActive: boolean;
  triggerSOS: () => void;
  cancelSOS: () => void;
}

// 2. We create the actual store
export const useEmergencyStore = create<EmergencyState>((set) => ({
  // Initial state (when the app first loads, SOS is false)
  isSOSActive: false,
  
  // Action to turn it on
  triggerSOS: () => set({ isSOSActive: true }),
  
  // Action to turn it off
  cancelSOS: () => set({ isSOSActive: false }),
}));