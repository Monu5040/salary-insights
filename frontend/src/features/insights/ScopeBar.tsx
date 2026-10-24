import { Select, Typography } from "antd";

import { Toolbar } from "../../components/Toolbar";
import { useCurrencies } from "../reference/hooks";
import { ReferenceFilters } from "../reference/ReferenceFilters";
import type { Changes } from "./scope";

type Props = {
  params: URLSearchParams;
  onChange: (changes: Changes) => void;
  /** What the answers use when the address doesn't say: the reporting currency. */
  currency: string;
};

const prefix = (words: string) => <Typography.Text type="secondary">{words}</Typography.Text>;

/** The currency and filters every insight on the page follows. */
export function ScopeBar({ params, onChange, currency }: Props) {
  const currencies = useCurrencies().data ?? [];
  return (
    <Toolbar>
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
