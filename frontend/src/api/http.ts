/** Field errors as the API sends them: a list per field, nested for nested objects. */
export type FieldErrors = { [field: string]: string[] | FieldErrors };

/** An RFC 9457 problem, with the extra fields our API adds (design §7). */
export type Problem = {
  status: number;
  detail?: string;
  errors?: FieldErrors;
  /** 409: the record the request clashes with. */
  existing_id?: number;
  /** 412: the version the server has now. */
  current_version?: number;
  /** The request's id in the server's logs, to quote when reporting a fault. */
  request_id?: string;
};

/** A failed call to our API. `message` is the server's explanation when it sent one. */
export class HttpError extends Error {
  /** 0 when the server couldn't be reached at all. */
  readonly status: number;
  readonly problem?: Problem;
  /** Finds the request in the server's logs (design §7), when the server answered. */
  readonly requestId?: string;

  constructor(status: number, message: string, problem?: Problem, requestId?: string) {
    super(message);
    this.status = status;
    this.problem = problem;
    this.requestId = requestId;
  }
}

type Write = "POST" | "PUT" | "PATCH" | "DELETE";

/** The header every write to a versioned record sends: the version on screen (design §5). */
export const ifMatch = (version: number) => ({ "If-Match": `"${version}"` });

/** GET JSON from our own API. */
export function getJson<T>(url: string): Promise<T> {
  return request<T>(url, { headers: { Accept: "application/json" } });
}

/** Send a write to our API. 204 resolves to undefined. */
export function sendJson<T>(
  method: Write,
  url: string,
  body?: unknown,
  headers: Record<string, string> = {},
): Promise<T> {
  return request<T>(url, {
    method,
    headers: { Accept: "application/json", "Content-Type": "application/json", ...headers },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

async function request<T>(url: string, init: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, { ...init, credentials: "same-origin" });
  } catch {
    throw new HttpError(0, "Can't reach the server. Check your connection and try again.");
  }
  if (!response.ok) {
    const problem = await readProblem(response);
    const message = problem?.detail || `${response.status} ${response.statusText}`.trim();
    // A proxy's error page has no problem body, but the request id header may still be there.
    const requestId = problem?.request_id ?? response.headers.get("X-Request-ID") ?? undefined;
    throw new HttpError(response.status, message, problem, requestId);
  }
  return (response.status === 204 ? undefined : await response.json()) as T;
}

/** The RFC 9457 problem that every API error carries, if the body is one. */
async function readProblem(response: Response): Promise<Problem | undefined> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object") return body as Problem;
  } catch {
    // Not JSON, such as a proxy's error page.
  }
  return undefined;
}
