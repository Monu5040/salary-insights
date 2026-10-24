import { getJson } from "./http";

export type Country = { code: string; name: string; default_currency: string; locale: string };
export type Department = { id: number; name: string };
export type Currency = { code: string; name: string; minor_units: number; usd_per_unit: string };
export type Config = { reporting_currency: string; today: string };

export const fetchCountries = () => getJson<Country[]>("/api/v1/reference/countries/");
export const fetchDepartments = () => getJson<Department[]>("/api/v1/reference/departments/");
export const fetchCurrencies = () => getJson<Currency[]>("/api/v1/reference/currencies/");
export const fetchConfig = () => getJson<Config>("/api/v1/config/");
