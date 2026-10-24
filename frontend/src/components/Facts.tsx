import { theme } from "antd";
import type { ReactNode } from "react";

export type Fact = { label: string; value: ReactNode };

/** Labels and their values in a grid, each small label above its value. */
export function Facts({ items, width = 160 }: { items: Fact[]; width?: number }) {
  const { token } = theme.useToken();
  return (
    <dl
      style={{
        display: "grid",
        gridTemplateColumns: `repeat(auto-fill, minmax(${width}px, 1fr))`,
        gap: "16px 24px",
        margin: 0,
      }}
    >
      {items.map((item) => (
        <div key={item.label} style={{ minWidth: 0 }}>
          <dt style={{ color: token.colorTextSecondary, fontSize: 12, marginBottom: 2 }}>
            {item.label}
          </dt>
          <dd style={{ margin: 0, fontWeight: 500, overflowWrap: "anywhere" }}>{item.value}</dd>
        </div>
      ))}
    </dl>
  );
}
