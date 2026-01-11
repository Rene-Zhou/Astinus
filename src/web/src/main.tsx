import React from "react";
import ReactDOM from "react-dom/client";
import "./index.css";
import "./utils/i18n";
import App from "./App";

const rootElement = document.getElementById("root");

if (!rootElement) {
  throw new Error(
    "Root element #root not found. Please ensure index.html has a div#root.",
  );
}

ReactDOM.createRoot(rootElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
