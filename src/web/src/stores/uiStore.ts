import { create } from "zustand";
import { immer } from "zustand/middleware/immer";

type Language = "cn" | "en";
type Theme = "light" | "dark";
export type MobilePanelType = "character" | "dice" | "menu" | null;

export interface UIState {
  language: Language;
  theme: Theme;
  sidebarOpen: boolean;
  diceRollerVisible: boolean;
  mobileActivePanel: MobilePanelType;

  setLanguage: (lang: Language) => void;
  toggleTheme: () => void;
  toggleSidebar: () => void;
  setDiceRollerVisible: (visible: boolean) => void;
  setMobileActivePanel: (panel: MobilePanelType) => void;
  closeMobilePanel: () => void;
}

const initialState: Omit<
  UIState,
  | "setLanguage"
  | "toggleTheme"
  | "toggleSidebar"
  | "setDiceRollerVisible"
  | "setMobileActivePanel"
  | "closeMobilePanel"
> = {
  language: "cn",
  theme: "light",
  sidebarOpen: true,
  diceRollerVisible: false,
  mobileActivePanel: null,
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

    setMobileActivePanel: (panel) =>
      set((state) => {
        state.mobileActivePanel = panel;
      }),

    closeMobilePanel: () =>
      set((state) => {
        state.mobileActivePanel = null;
      }),
  })),
);
