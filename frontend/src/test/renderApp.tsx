import { QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import { MemoryRouter } from "react-router";

import { App } from "../App";
import { createQueryClient } from "../lib/queryClient";

/** The whole app at a URL, with the real query client (no retries). Returns that client. */
export function renderApp(path: string) {
  const client = createQueryClient({ retries: 0 });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[path]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return client;
}
