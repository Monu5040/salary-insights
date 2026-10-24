import type { FormInstance } from "antd";

import { type FieldErrors, HttpError } from "../api/http";

export type FieldError = { name: string[]; errors: string[] };

/** The API's field errors as form fields: {salary: {amount: ["…"]}} → salary.amount. */
export function toFieldErrors(errors: FieldErrors, path: string[] = []): FieldError[] {
  return Object.entries(errors).flatMap(([field, value]) =>
    Array.isArray(value)
      ? [{ name: [...path, field], errors: value }]
      : toFieldErrors(value, [...path, field]),
  );
}

/** Put a failed save's field errors under the fields they belong to. `rename` moves an
 *  error to the field that is on screen, such as a % box standing in for the amount. */
export function showFieldErrors(
  form: FormInstance,
  error: unknown,
  rename: Record<string, string> = {},
): void {
  if (!(error instanceof HttpError && error.problem?.errors)) return;
  const errors = Object.fromEntries(
    Object.entries(error.problem.errors).map(([field, value]) => [rename[field] ?? field, value]),
  );
  form.setFields(toFieldErrors(errors));
}
