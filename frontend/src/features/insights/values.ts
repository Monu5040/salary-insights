import type { Group, Metric } from "../../api/insights";

/** A group's name: its labels, such as "India · Engineering". */
export const groupName = (group: Group) => Object.values(group.labels).join(" · ") || "Everyone";

/** A metric's value as text: a count, or an amount in the answer's currency. */
export function showValue(
  metric: Metric,
  value: string | null | undefined,
  money: (amount: string | null) => string,
): string {
  if (value === null || value === undefined) return "–";
  return metric === "headcount" ? Number(value).toLocaleString("en") : money(value);
}
