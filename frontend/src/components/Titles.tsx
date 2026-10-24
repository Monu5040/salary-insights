import { Typography } from "antd";
import { type CSSProperties, useEffect } from "react";

/**
 * The page's one top-level heading. It also names the browser tab, which is what a screen
 * reader announces on arriving at a page (WCAG 2.4.2).
 */
export function PageTitle({ children, style }: { children: string; style?: CSSProperties }) {
  useEffect(() => {
    document.title = `${children} · Salary Insights`;
  }, [children]);
  return (
    <Typography.Title
      level={1}
      style={{ fontSize: 26, lineHeight: 1.3, letterSpacing: "-0.02em", marginTop: 0, ...style }}
    >
      {children}
    </Typography.Title>
  );
}

/** A card's title as a heading under the page's, so a screen reader can jump between cards. */
export function CardTitle({ children }: { children: string }) {
  return (
    <Typography.Title level={2} style={{ fontSize: 16, margin: 0 }}>
      {children}
    </Typography.Title>
  );
}
