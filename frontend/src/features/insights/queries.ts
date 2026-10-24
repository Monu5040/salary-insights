import { keepPreviousData, useMutation, useQuery } from "@tanstack/react-query";

import { ask, fetchExplore, fetchPayEquity, fetchPresets, fetchSummary } from "../../api/insights";

/** One insight's answer for a query string. The previous answer stays on screen while a new
 *  currency or filter loads. */
function useAnswer<T>(name: string, query: string, fetch: (query: string) => Promise<T>) {
  return useQuery({
    queryKey: ["insights", name, query],
    queryFn: () => fetch(query),
    placeholderData: keepPreviousData,
  });
}

export const useSummary = (scope: string) => useAnswer("summary", scope, fetchSummary);
export const useExplore = (query: string) => useAnswer("explore", query, fetchExplore);
export const usePayEquity = (query: string) => useAnswer("pay-equity", query, fetchPayEquity);

/** A question in plain English. A mutation, not a query: each one is a call to Groq. */
export const useAsk = () => useMutation({ mutationFn: ask });

export const usePresets = () =>
  useQuery({ queryKey: ["insights", "presets"], queryFn: fetchPresets, staleTime: Infinity });
