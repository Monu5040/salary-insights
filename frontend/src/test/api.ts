import { vi } from "vitest";

import type { Employee } from "../api/employees";

type Handler = (init?: RequestInit, url?: string) => Response | Promise<Response>;

/** Replace fetch with handlers keyed by "METHOD /path", with or without its query string.
 *  Any other request gets a 404. */
export function stubApi(routes: Record<string, Handler>) {
  const fetchMock = vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const method = init?.method ?? "GET";
    const url = String(input);
    const handler = routes[`${method} ${url}`] ?? routes[`${method} ${url.split("?")[0]}`];
    return handler ? handler(init, url) : new Response(null, { status: 404 });
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

/** The URLs of the requests made so far, for one method. */
export function requested(fetchMock: ReturnType<typeof stubApi>, method = "GET"): string[] {
  return fetchMock.mock.calls
    .filter(([, init]) => (init?.method ?? "GET") === method)
    .map(([url]) => String(url));
}

/** The JSON body and headers of the last request with this method. */
export function lastSent(fetchMock: ReturnType<typeof stubApi>, method: string) {
  const call = fetchMock.mock.calls.filter(([, init]) => init?.method === method).at(-1);
  const init = call?.[1];
  return {
    body: init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : undefined,
    headers: init?.headers as Record<string, string> | undefined,
  };
}

export function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

/** An API error as the backend sends it (RFC 9457). */
export function problem(status: number, detail: string): Response {
  return new Response(JSON.stringify({ type: "about:blank", status, detail }), {
    status,
    headers: { "Content-Type": "application/problem+json" },
  });
}

/** Reference data and settings, as the forms and filters load them. */
export const REFERENCE = {
  "GET /api/v1/reference/countries/": () =>
    json([
      { code: "IN", name: "India", default_currency: "INR", locale: "en-IN" },
      { code: "US", name: "United States", default_currency: "USD", locale: "en-US" },
    ]),
  "GET /api/v1/reference/departments/": () =>
    json([
      { id: 1, name: "Engineering" },
      { id: 2, name: "Sales" },
    ]),
  "GET /api/v1/reference/currencies/": () =>
    json([
      { code: "INR", name: "Indian rupee", minor_units: 2, usd_per_unit: "0.0115000000" },
      { code: "USD", name: "US dollar", minor_units: 2, usd_per_unit: "1.0000000000" },
    ]),
  "GET /api/v1/config/": () =>
    json({ reporting_currency: "USD", today: "2026-09-30" }),
  "GET /readyz/": () => json({ status: "ok" }),
};

export const ASHA: Employee = {
  id: 7,
  employee_code: "E00007",
  full_name: "Asha Rao",
  country: { code: "IN", name: "India" },
  department: { id: 1, name: "Engineering" },
  job_title: "Data Analyst",
  hire_date: "2024-01-15",
  salary: "1800000.00",
  currency: "INR",
  email: "asha.rao@acme.example",
  version: 3,
  updated_at: "2026-05-01T09:00:00Z",
};
