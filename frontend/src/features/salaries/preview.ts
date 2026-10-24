import type { SalaryRow } from "../../api/employees";
import { applyRaise, isAmount, raisePercent } from "../../lib/money";

export const PERCENT = /^-?\d+(\.\d+)?$/;

/** The change in force the day before `day`: what a new change is a raise from. */
export function inForceBefore(records: SalaryRow[], day: string): SalaryRow | undefined {
  return records.find((row) => row.effective_date < day); // records are newest first
}

const positive = (amount: string) => !amount.startsWith("-") && /[1-9]/.test(amount);

/** The amount a change saves: typed, or the previous amount raised by the %, rounded the
 *  server's way. Undefined until the inputs make sense. */
export function proposedAmount(
  mode: "amount" | "percent",
  input: { amount?: string; percent?: string; currency?: string },
  before: SalaryRow | undefined,
  decimals: number,
): string | undefined {
  const { amount = "", percent = "", currency } = input;
  if (mode === "amount") {
    return isAmount(amount, decimals) && positive(amount) ? amount.trim() : undefined;
  }
  if (!before || currency !== before.currency || !PERCENT.test(percent.trim())) return undefined;
  const raised = applyRaise(before.amount, percent.trim(), decimals);
  return positive(raised) ? raised : undefined;
}

/** "+7.0%" or "-5.0%" */
export function signedPercent(before: string, after: string): string {
  const percent = raisePercent(before, after);
  return `${percent.startsWith("-") ? "" : "+"}${percent}%`;
}
