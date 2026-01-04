import { create } from "zustand";
import { immer } from "zustand/middleware/immer";

type Language = "cn" | "en";
type Theme = "light" | "dark";

export interface UIState {
  language: Language;
  theme: Theme;
  sidebarOpen: boolean;
  diceRollerVisible: boolean;

  setLanguage: (lang: Language) => void;
  toggleTheme: () => void;
  toggleSidebar: () => void;
  setDiceRollerVisible: (visible: boolean) => void;
}

const initialState: Omit<
  UIState,
  "setLanguage" | "toggleTheme" | "toggleSidebar" | "setDiceRollerVisible"
> = {
  language: "cn",
  theme: "light",
  sidebarOpen: true,
  diceRollerVisible: false,
};

export const useUIStore = create<UIState>()(
  immer((set) => ({
    ...initialState,

    setLanguage: (lang) =>
      set((state) => {
        state.language = lang;
      }),

    toggleTheme: () =>
      set((state) => {
        state.theme = state.theme === "light" ? "dark" : "light";
      }),

    toggleSidebar: () =>
      set((state) => {
        state.sidebarOpen = !state.sidebarOpen;
      }),

    setDiceRollerVisible: (visible) =>
      set((state) => {
        state.diceRollerVisible = visible;
      }),
  })),
);
