import { Button, Card, Typography } from "antd";
import { useState } from "react";

import type { Employee } from "../../api/employees";
import { CardTitle } from "../../components/Titles";
import { ChangeSalaryModal } from "./ChangeSalaryModal";
import { useMoney } from "./useMoney";

/** The current annual gross base salary, and the way to change it. */
export function SalaryCard({ employee }: { employee: Employee }) {
  const money = useMoney(employee.country.code);
  const [changing, setChanging] = useState(false);

  return (
    <Card
      title={<CardTitle>Salary</CardTitle>}
      style={{ marginBottom: 16, height: "calc(100% - 16px)" }}
      extra={
        <Button type="primary" onClick={() => setChanging(true)}>
          Change salary
        </Button>
      }
    >
      <Typography.Text strong style={{ fontSize: 32, letterSpacing: "-0.02em" }}>
        {money.show(employee.salary, employee.currency)}
      </Typography.Text>
      <Typography.Paragraph type="secondary" style={{ margin: "4px 0 0" }}>
        A year, gross base pay, in {employee.currency}.
      </Typography.Paragraph>
      <ChangeSalaryModal employee={employee} open={changing} onClose={() => setChanging(false)} />
    </Card>
  );
}
