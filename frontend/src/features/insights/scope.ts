import { useSearchParams } from "react-router";

/** What every insight on the page is relative to, kept in the page address (design §8). */
export const SCOPE_PARAMS = ["currency", "country", "department"] as const;

export type Changes = Record<string, string | string[] | undefined>;

/** The page's scope as a query string for the API, and a way to change it. */
export function useScope() {
  const [params, setParams] = useSearchParams();
  const scope = new URLSearchParams();
  for (const key of SCOPE_PARAMS) {
    for (const value of params.getAll(key)) scope.append(key, value);
  }

  function update(changes: Changes) {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      next.delete(key);
      for (const item of [value ?? []].flat()) next.append(key, item);
    }
    setParams(next);
  }

  return { params, scope: scope.toString(), update };
}

/** A query string: the scope, plus more parameters. */
export function withScope(scope: string, extra: Record<string, string[]>): string {
  const query = new URLSearchParams(scope);
  for (const [key, values] of Object.entries(extra)) {
    for (const value of values) query.append(key, value);
  }
  return query.toString();
}
