import { useEffect } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import Layout from "./components/Layout/Header";
import MenuPage from "./pages/MenuPage";
import GamePage from "./pages/GamePage";
import CharacterPage, { NotFoundPage } from "./pages/CharacterPage";
import SettingsPage from "./pages/SettingsPage";
import SavesPage from "./pages/SavesPage";
import { useUIStore } from "./stores/uiStore";

function App() {
  const theme = useUIStore((state) => state.theme);

  useEffect(() => {
    const root = window.document.documentElement;
    if (theme === "dark") {
      root.classList.add("dark");
      root.style.colorScheme = "dark";
    } else {
      root.classList.remove("dark");
      root.style.colorScheme = "light";
    }
  }, [theme]);

  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<MenuPage />} />
          <Route path="/game" element={<GamePage />} />
          <Route path="/character" element={<CharacterPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/saves" element={<SavesPage />} />
          <Route path="/404" element={<NotFoundPage />} />
          <Route path="*" element={<Navigate to="/404" replace />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}

export default App;
