import { formatCompact, formatMoney } from "../../lib/money";
import { useCountries, useCurrencies } from "../reference/hooks";

/** Amounts in the answer's currency, written the way a country using it writes them. */
export function useCurrency(currency: string) {
  const countries = useCountries().data ?? [];
  const currencies = useCurrencies().data ?? [];
  const locale =
    countries.find((row) => row.default_currency === currency)?.locale ??
    (currency === "USD" ? "en-US" : "en");
  const decimals = currencies.find((row) => row.code === currency)?.minor_units ?? 2;
  return {
    money: (amount: string | null) =>
      amount === null ? "" : formatMoney(amount, currency, locale, decimals),
    compact: (amount: string | null) =>
      amount === null ? "" : formatCompact(amount, currency, locale),
  };
}
