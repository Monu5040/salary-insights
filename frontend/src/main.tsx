import "@fontsource-variable/inter";

import { QueryClientProvider } from "@tanstack/react-query";
import { ConfigProvider } from "antd";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router";

import "./app.css";
import { App } from "./App";
import { queryClient } from "./lib/queryClient";
import { card, theme } from "./lib/theme";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <ConfigProvider theme={theme} card={card}>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ConfigProvider>
    </QueryClientProvider>
  </StrictMode>,
);
