import { Input, Select, Typography } from "antd";

import { Toolbar } from "../../components/Toolbar";
import { useConfig, useCurrencies } from "../reference/hooks";
import { ReferenceFilters } from "../reference/ReferenceFilters";
import type { Changes } from "./scope";

type Props = {
  params: URLSearchParams;
  onChange: (changes: Changes) => void;
  /** What the answers use when the address doesn't say: the reporting currency. */
  currency: string;
};

const prefix = (words: string) => <Typography.Text type="secondary">{words}</Typography.Text>;

/** The day, currency and filters every insight on the page follows. */
export function ScopeBar({ params, onChange, currency }: Props) {
  const currencies = useCurrencies().data ?? [];
  const today = useConfig().data?.today ?? "";
  return (
    <Toolbar>
      <Input
        type="date"
        aria-label="As of"
        prefix={prefix("As of")}
        value={params.get("as_of") ?? today}
        max="9999-12-31"
        // Today is the default, so it isn't written into the address.
        onChange={(event) => {
          const day = event.target.value;
          onChange({ as_of: day && day !== today ? day : undefined });
        }}
        style={{ width: 200 }}
      />
      <Select
        showSearch
        virtual={false}
        aria-label="Currency"
        prefix={prefix("Currency")}
        value={currency}
        options={currencies.map((row) => ({ value: row.code, label: `${row.code} ${row.name}` }))}
        onChange={(code: string) => onChange({ currency: code })}
        style={{ width: 260 }}
      />
      <ReferenceFilters params={params} onChange={onChange} />
    </Toolbar>
  );
}
