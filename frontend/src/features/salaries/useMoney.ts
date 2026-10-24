import { formatMoney } from "../../lib/money";
import { useCountries, useCurrencies } from "../reference/hooks";

/** Currency picker options: "INR Indian rupee". */
export function useCurrencyOptions() {
  const currencies = useCurrencies().data ?? [];
  return currencies.map((row) => ({ value: row.code, label: `${row.code} ${row.name}` }));
}

/** Amounts written the way the employee's country writes them, and each currency's decimals. */
export function useMoney(countryCode: string) {
  const countries = useCountries().data ?? [];
  const currencies = useCurrencies().data ?? [];
  const locale = countries.find((row) => row.code === countryCode)?.locale ?? "en";
  const decimals = (currency: string) =>
    currencies.find((row) => row.code === currency)?.minor_units ?? 2;
  return {
    decimals,
    show: (amount: string, currency: string) =>
      formatMoney(amount, currency, locale, decimals(currency)),
  };
}
