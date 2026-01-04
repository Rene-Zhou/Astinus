import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import type { ConnectionStatus } from "../api/types";

export interface ConnectionStoreState {
  status: ConnectionStatus;
  error: string | null;
  reconnectAttempts: number;

  setStatus: (status: ConnectionStatus) => void;
  setError: (error: string | null) => void;
  incrementReconnectAttempts: () => void;
  resetReconnectAttempts: () => void;
}

const initialState: Omit<
  ConnectionStoreState,
  "setStatus" | "setError" | "incrementReconnectAttempts" | "resetReconnectAttempts"
> = {
  status: "disconnected",
  error: null,
  reconnectAttempts: 0,
};

export const useConnectionStore = create<ConnectionStoreState>()(
  immer((set) => ({
    ...initialState,

    setStatus: (status) =>
      set((state) => {
        state.status = status;
      }),

    setError: (error) =>
      set((state) => {
        state.error = error;
      }),

    incrementReconnectAttempts: () =>
      set((state) => {
        state.reconnectAttempts += 1;
      }),

    resetReconnectAttempts: () =>
      set((state) => {
        state.reconnectAttempts = 0;
      }),
  })),
);
