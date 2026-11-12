import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./app/App";
import { backendFromEnv } from "./shared/auth";
import "./shared/styles/global.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App backend={backendFromEnv()} />
  </StrictMode>,
);
