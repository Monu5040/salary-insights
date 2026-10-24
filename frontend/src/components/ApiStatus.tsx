import { useQuery } from "@tanstack/react-query";

import { getJson } from "../api/http";

/** Whether the backend can serve requests, from its readiness probe: a dot and its words. */
export function ApiStatus() {
  const { isPending, isSuccess } = useQuery({
    queryKey: ["readyz"],
    queryFn: () => getJson<{ status: string }>("/readyz/"),
    refetchInterval: 30_000,
  });

  const [state, words] = isPending
    ? ["checking", "API: checking…"]
    : isSuccess
      ? ["ready", "API: ready"]
      : ["down", "API: unavailable"];
  return (
    <span className="api-status">
      <span aria-hidden className={`api-dot api-dot-${state}`} />
      <span>{words}</span>
    </span>
  );
}
