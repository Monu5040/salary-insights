import { QueryClient } from "@tanstack/react-query";

import { HttpError } from "../api/http";

const isClientError = (error: unknown) =>
  error instanceof HttpError && error.status >= 400 && error.status < 500;

/** Client errors aren't retried; anything else is retried `retries` times. */
export function createQueryClient({ retries = 1 } = {}): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: (failures, error) => !isClientError(error) && failures < retries,
        refetchOnWindowFocus: false,
      },
    },
  });
}

export const queryClient = createQueryClient();
