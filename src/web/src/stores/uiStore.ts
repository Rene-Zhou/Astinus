import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import { persist } from "zustand/middleware";

type Language = "cn" | "en";
type Theme = "light" | "dark";
type AnimationSpeed = "slow" | "normal" | "fast";
export type MobilePanelType = "character" | "dice" | "menu" | null;

export interface UIState {
  language: Language;
  theme: Theme;
  animationSpeed: AnimationSpeed;
  sidebarOpen: boolean;
  diceRollerVisible: boolean;
  mobileActivePanel: MobilePanelType;

  setLanguage: (lang: Language) => void;
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  setAnimationSpeed: (speed: AnimationSpeed) => void;
  toggleSidebar: () => void;
  setDiceRollerVisible: (visible: boolean) => void;
  setMobileActivePanel: (panel: MobilePanelType) => void;
  closeMobilePanel: () => void;
}

const initialState: Omit<
  UIState,
  | "setLanguage"
  | "setTheme"
  | "toggleTheme"
  | "setAnimationSpeed"
  | "toggleSidebar"
  | "setDiceRollerVisible"
  | "setMobileActivePanel"
  | "closeMobilePanel"
> = {
  language: "cn",
  theme: "dark",
  animationSpeed: "normal",
  sidebarOpen: true,
  diceRollerVisible: false,
  mobileActivePanel: null,
};

export const useUIStore = create<UIState>()(
  persist(
    immer((set) => ({
      ...initialState,

      setLanguage: (lang) =>
        set((state) => {
          state.language = lang;
        }),

      setTheme: (theme) =>
        set((state) => {
          state.theme = theme;
        }),

      toggleTheme: () =>
        set((state) => {
          state.theme = state.theme === "light" ? "dark" : "light";
        }),

      setAnimationSpeed: (speed) =>
        set((state) => {
          state.animationSpeed = speed;
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
    {
      name: "astinus-ui-storage",
      partialize: (state) => ({
        language: state.language,
        theme: state.theme,
        animationSpeed: state.animationSpeed,
      }),
    }
  )
);
