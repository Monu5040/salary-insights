import { InfoCircleOutlined, RiseOutlined, TeamOutlined, WalletOutlined } from "@ant-design/icons";
import { Card, Col, Flex, Row, Statistic, Typography } from "antd";
import type { ReactNode } from "react";

import type { Summary } from "../../api/insights";
import { useCurrency } from "./useCurrency";

/** Headcount, payroll and the median and mean salary, and how they were converted. */
export function Headline({ summary }: { summary: Summary }) {
  const { money, compact } = useCurrency(summary.currency);

  return (
    <>
      <Row gutter={[16, 16]}>
        <Col xs={24} md={8}>
          <Figure
            icon={<TeamOutlined />}
            tint={["#eef2ff", "#4f46e5"]}
            title="Headcount"
            value={summary.headcount.toLocaleString("en")}
            caption="Full-time employees"
          />
        </Col>
        <Col xs={24} md={8}>
          <Figure
            icon={<WalletOutlined />}
            tint={["#ecfdf5", "#059669"]}
            title="Payroll, a year"
            value={compact(summary.payroll)}
            caption={money(summary.payroll)}
          />
        </Col>
        <Col xs={24} md={8}>
          <Figure
            icon={<RiseOutlined />}
            tint={["#fff7ed", "#ea580c"]}
            title="Median salary"
            value={money(summary.median) || "–"}
            caption={summary.mean ? `Mean ${money(summary.mean)}` : "Nobody in scope"}
          />
        </Col>
      </Row>
      <Flex gap={8} align="baseline" style={{ margin: "12px 0 20px" }}>
        <Typography.Text type="secondary">
          <InfoCircleOutlined aria-hidden />
        </Typography.Text>
        <Typography.Paragraph type="secondary" style={{ margin: 0 }}>
          Annual gross base salaries in {summary.currency}. {summary.fx_basis}.
        </Typography.Paragraph>
      </Flex>
    </>
  );
}

type FigureProps = {
  icon: ReactNode;
  /** The icon's background and colour. */
  tint: [string, string];
  title: string;
  value: string;
  caption: string;
};

/** One headline number, with an icon to tell it apart at a glance. */
function Figure({ icon, tint: [background, color], title, value, caption }: FigureProps) {
  return (
    <Card styles={{ body: { padding: 20 } }} style={{ height: "100%" }}>
      <Flex justify="space-between" align="flex-start" gap={12}>
        <Statistic title={title} value={value} valueStyle={{ fontWeight: 600 }} />
        <span
          aria-hidden
          style={{
            display: "grid",
            placeItems: "center",
            flex: "none",
            width: 40,
            height: 40,
            borderRadius: 10,
            background,
            color,
            fontSize: 18,
          }}
        >
          {icon}
        </span>
      </Flex>
      <Typography.Text type="secondary" style={{ fontSize: 12 }}>
        {caption}
      </Typography.Text>
    </Card>
  );
}
