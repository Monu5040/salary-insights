import { Flex, theme } from "antd";
import type { ReactNode } from "react";

/** Filters on a white bar above what they filter; `extra` sits at its right-hand end. */
export function Toolbar({ children, extra }: { children: ReactNode; extra?: ReactNode }) {
  const { token } = theme.useToken();
  return (
    <Flex
      gap={8}
      wrap
      align="center"
      style={{
        marginBottom: 16,
        padding: 12,
        background: token.colorBgContainer,
        border: `1px solid ${token.colorBorderSecondary}`,
        borderRadius: token.borderRadiusLG,
      }}
    >
      {children}
      {extra && <div style={{ marginLeft: "auto" }}>{extra}</div>}
    </Flex>
  );
}
