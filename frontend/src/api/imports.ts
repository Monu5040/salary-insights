import { sendForm } from "./http";

export type DateFormat = "iso" | "dmy" | "mdy";

/** What a sheet would change, before anything is changed (design §6). */
export type ImportPreview = {
  rows: number;
  creates: number;
  changes: number;
  unchanged: number;
  error_rows: number;
  ignored_columns: string[];
  new_employees: { line: number; employee_code: string; full_name: string; salary: string }[];
  changed_employees: {
    line: number;
    employee_code: string;
    full_name: string;
    fields: Record<string, [unknown, unknown]>;
    salary: string | null;
  }[];
  row_errors: { line: number; column: string; message: string }[];
  /** Sent back with the same file to apply exactly this plan. */
  fingerprint: string;
};

export type Applied = { creates: number; changes: number; unchanged: number };

function form(file: File, dateFormat: DateFormat, fingerprint?: string): FormData {
  const data = new FormData();
  data.append("file", file);
  data.append("date_format", dateFormat);
  if (fingerprint) data.append("fingerprint", fingerprint);
  return data;
}

export const previewImport = (file: File, dateFormat: DateFormat) =>
  sendForm<ImportPreview>("/api/v1/imports/preview/", form(file, dateFormat));

export const applyImport = (file: File, dateFormat: DateFormat, fingerprint: string) =>
  sendForm<Applied>("/api/v1/imports/apply/", form(file, dateFormat, fingerprint));
