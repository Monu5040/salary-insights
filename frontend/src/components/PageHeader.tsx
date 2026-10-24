import { Breadcrumb, type BreadcrumbProps, Flex, Typography } from "antd";
import type { ReactNode } from "react";

import { PageTitle } from "./Titles";

type Props = {
  title: string;
  /** A line under the title about what the page is for. */
  subtitle?: ReactNode;
  /** The page's actions, on the right. */
  extra?: ReactNode;
  /** Where the page sits, above the title. */
  breadcrumb?: BreadcrumbProps["items"];
};

/** The top of a page: where it sits, its heading, a line about it, and its actions. */
export function PageHeader({ title, subtitle, extra, breadcrumb }: Props) {
  return (
    <div style={{ marginBottom: 24 }}>
      {breadcrumb && <Breadcrumb items={breadcrumb} style={{ marginBottom: 8 }} />}
      <Flex justify="space-between" align="flex-end" gap={16} wrap>
        <div style={{ minWidth: 0 }}>
          <PageTitle style={{ marginBottom: 0 }}>{title}</PageTitle>
          {subtitle && (
            <Typography.Paragraph type="secondary" style={{ margin: "4px 0 0" }}>
              {subtitle}
            </Typography.Paragraph>
          )}
        </div>
        {extra && <Flex gap={8}>{extra}</Flex>}
      </Flex>
    </div>
  );
}
