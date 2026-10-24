import { applyRaise, isAmount, raisePercent } from "../../lib/money";

export const PERCENT = /^-?\d+(\.\d+)?$/;

const positive = (amount: string) => !amount.startsWith("-") && /[1-9]/.test(amount);

/** The amount a change saves: typed, or the current amount raised by the %, rounded the
 *  server's way. Undefined until the inputs make sense. */
export function proposedAmount(
  mode: "amount" | "percent",
  input: { amount?: string; percent?: string },
  current: string,
  decimals: number,
): string | undefined {
  const { amount = "", percent = "" } = input;
  if (mode === "amount") {
    return isAmount(amount, decimals) && positive(amount) ? amount.trim() : undefined;
  }
  if (!PERCENT.test(percent.trim())) return undefined;
  const raised = applyRaise(current, percent.trim(), decimals);
  return positive(raised) ? raised : undefined;
}

/** "+7.0%" or "-5.0%" */
export function signedPercent(before: string, after: string): string {
  const percent = raisePercent(before, after);
  return `${percent.startsWith("-") ? "" : "+"}${percent}%`;
}
