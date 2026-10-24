import type { Reason } from "../../api/employees";

export const REASONS: Record<Reason, string> = {
  hire: "Starting salary",
  merit: "Merit",
  promotion: "Promotion",
  market: "Market adjustment",
  transfer: "Transfer",
  correction: "Correction (not a raise)",
};

/** Reasons a new change can have: the starting salary is set when the employee is added. */
export const NEW_REASONS = (Object.keys(REASONS) as Reason[]).filter((reason) => reason !== "hire");
