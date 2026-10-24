import { HttpError } from "../api/http";

/** The reference to quote for a fault on the server's side, which finds it in the logs. */
export function errorReference(error: unknown): string | undefined {
  return error instanceof HttpError && error.status >= 500 ? error.requestId : undefined;
}
