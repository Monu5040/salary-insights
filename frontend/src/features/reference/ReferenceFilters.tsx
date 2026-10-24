import { Select } from "antd";

import { useCountries, useDepartments } from "./hooks";

type Props = {
  params: URLSearchParams;
  onChange: (changes: Record<string, string[]>) => void;
};

/** Country and department filters, read from and written to the page address. */
export function ReferenceFilters({ params, onChange }: Props) {
  const countries = useCountries().data ?? [];
  const departments = useDepartments().data ?? [];
  const common = {
    mode: "multiple",
    allowClear: true,
    virtual: false,
    maxTagCount: "responsive",
  } as const;

  return (
    <>
      <Select
        {...common}
        placeholder="Country"
        aria-label="Country"
        value={params.getAll("country")}
        options={countries.map((row) => ({ value: row.code, label: row.name }))}
        onChange={(country: string[]) => onChange({ country })}
        style={{ minWidth: 170 }}
      />
      <Select
        {...common}
        placeholder="Department"
        aria-label="Department"
        value={params.getAll("department")}
        options={departments.map((row) => ({ value: String(row.id), label: row.name }))}
        onChange={(department: string[]) => onChange({ department })}
        style={{ minWidth: 190 }}
      />
    </>
  );
}
