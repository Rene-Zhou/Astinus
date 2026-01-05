import { create } from "zustand";
import { immer } from "zustand/middleware/immer";

type Language = "cn" | "en";
type Theme = "light" | "dark";

export interface UIState {
  language: Language;
  theme: Theme;
  sidebarOpen: boolean;
  diceRollerVisible: boolean;

  // Mobile panel states
  mobileStatBlockOpen: boolean;
  mobileDiceRollerOpen: boolean;

  setLanguage: (lang: Language) => void;
  toggleTheme: () => void;
  toggleSidebar: () => void;
  setDiceRollerVisible: (visible: boolean) => void;

  // Mobile panel actions
  setMobileStatBlockOpen: (open: boolean) => void;
  setMobileDiceRollerOpen: (open: boolean) => void;
  toggleMobileStatBlock: () => void;
  toggleMobileDiceRoller: () => void;
}

const initialState: Omit<
  UIState,
  | "setLanguage"
  | "toggleTheme"
  | "toggleSidebar"
  | "setDiceRollerVisible"
  | "setMobileStatBlockOpen"
  | "setMobileDiceRollerOpen"
  | "toggleMobileStatBlock"
  | "toggleMobileDiceRoller"
> = {
  language: "cn",
  theme: "light",
  sidebarOpen: true,
  diceRollerVisible: false,
  mobileStatBlockOpen: false,
  mobileDiceRollerOpen: false,
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

    setMobileStatBlockOpen: (open) =>
      set((state) => {
        state.mobileStatBlockOpen = open;
      }),

    setMobileDiceRollerOpen: (open) =>
      set((state) => {
        state.mobileDiceRollerOpen = open;
      }),

    toggleMobileStatBlock: () =>
      set((state) => {
        state.mobileStatBlockOpen = !state.mobileStatBlockOpen;
      }),

    toggleMobileDiceRoller: () =>
      set((state) => {
        state.mobileDiceRollerOpen = !state.mobileDiceRollerOpen;
      }),
  })),
);
