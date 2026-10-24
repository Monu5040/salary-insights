import { useQuery } from "@tanstack/react-query";

import {
  fetchConfig,
  fetchCountries,
  fetchCurrencies,
  fetchDepartments,
} from "../../api/reference";

// Reference data changes only with a release (it is loaded by migrations), so it is fetched
// once per session.
const options = { staleTime: Infinity } as const;

export const useCountries = () =>
  useQuery({ queryKey: ["reference", "countries"], queryFn: fetchCountries, ...options });
export const useDepartments = () =>
  useQuery({ queryKey: ["reference", "departments"], queryFn: fetchDepartments, ...options });
export const useCurrencies = () =>
  useQuery({ queryKey: ["reference", "currencies"], queryFn: fetchCurrencies, ...options });
export const useConfig = () => useQuery({ queryKey: ["config"], queryFn: fetchConfig, ...options });
