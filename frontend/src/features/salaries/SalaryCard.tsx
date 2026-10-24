import {
  Button,
  Card,
  Popconfirm,
  Space,
  Table,
  type TableColumnsType,
  Tag,
  theme,
  Typography,
} from "antd";
import { useState } from "react";

import type { Employee, SalaryRow } from "../../api/employees";
import { ErrorAlert } from "../../components/ErrorAlert";
import { CardTitle } from "../../components/Titles";
import { formatDate } from "../../lib/format";
import { useReloadEmployee } from "../employees/queries";
import { SaveError } from "../employees/SaveError";
import { CorrectChangeModal } from "./CorrectChangeModal";
import { REASONS } from "./labels";
import { useRemoveChange, useSalaries } from "./queries";
import { RecordChangeModal } from "./RecordChangeModal";
import { useMoney } from "./useMoney";

/** The salary over time, newest first, with each raise, and the ways to change it. */
export function SalaryCard({ employee }: { employee: Employee }) {
  const salaries = useSalaries(employee.id);
  const money = useMoney(employee.country.code);
  const remove = useRemoveChange(employee);
  const reload = useReloadEmployee(employee.id);
  const [recording, setRecording] = useState(false);
  const [correcting, setCorrecting] = useState<SalaryRow | null>(null);
  const history = salaries.data;
  const current = history?.records.find((row) => row.id === history.current_id);
  const { token } = theme.useToken();

  const columns: TableColumnsType<SalaryRow> = [
    {
      key: "from",
      title: "From",
      render: (_, row) => (
        <Space size={4}>
          {formatDate(row.effective_date)}
          {row.scheduled && (
            <Tag bordered={false} color="blue">
              Scheduled
            </Tag>
          )}
          {row.id === history?.current_id && (
            <Tag bordered={false} color="green">
              Current
            </Tag>
          )}
        </Space>
      ),
    },
    {
      key: "salary",
      title: "Salary (a year)",
      render: (_, row) => money.show(row.amount, row.currency),
    },
    {
      key: "change",
      title: "Change",
      render: (_, row) => {
        if (row.raise_percent !== null) {
          const cut = row.raise_percent.startsWith("-");
          return (
            <span style={{ color: cut ? token.colorError : token.green7, fontWeight: 500 }}>
              {`${cut ? "" : "+"}${row.raise_percent}%`}
            </span>
          );
        }
        return row.currency_change ? <Tag bordered={false}>Currency change</Tag> : "";
      },
    },
    {
      key: "reason",
      title: "Reason",
      render: (_, row) => (
        <>
          {REASONS[row.reason]}
          {row.note && <Typography.Text type="secondary"> · {row.note}</Typography.Text>}
        </>
      ),
    },
    {
      key: "actions",
      title: "",
      render: (_, row) => (
        <Space>
          <Button size="small" type="link" onClick={() => setCorrecting(row)}>
            Correct
          </Button>
          {row.reason !== "hire" && (
            <Popconfirm
              title="Remove this change?"
              description="Use this for a change entered by mistake or no longer planned."
              okText="Remove"
              onConfirm={() => remove.mutate(row.id)}
            >
              <Button size="small" type="link" danger>
                Remove
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <Card
      title={<CardTitle>Salary</CardTitle>}
      style={{ marginBottom: 16 }}
      loading={salaries.isPending}
      extra={
        history ? (
          <Button type="primary" onClick={() => setRecording(true)}>
            Record a change
          </Button>
        ) : null
      }
    >
      {salaries.error && (
        <ErrorAlert error={salaries.error} onRetry={() => void salaries.refetch()} />
      )}
      <SaveError
        error={remove.error}
        onReload={() => {
          remove.reset();
          void reload();
        }}
      />
      {history && (
        <>
          <Typography.Paragraph type="secondary" style={{ marginBottom: 16 }}>
            {current ? (
              <>
                <Typography.Text
                  strong
                  style={{ fontSize: 28, letterSpacing: "-0.02em", marginRight: 4 }}
                >
                  {money.show(current.amount, current.currency)}
                </Typography.Text>{" "}
                a year since {formatDate(current.effective_date)}, gross base pay
              </>
            ) : (
              "No salary in force today: their first one starts later."
            )}
          </Typography.Paragraph>
          <Table<SalaryRow>
            rowKey="id"
            size="small"
            columns={columns}
            dataSource={history.records}
            pagination={false}
            scroll={{ x: true }}
          />
          <RecordChangeModal
            employee={employee}
            history={history}
            open={recording}
            onClose={() => setRecording(false)}
          />
          <CorrectChangeModal
            employee={employee}
            history={history}
            change={correcting}
            onClose={() => setCorrecting(null)}
          />
        </>
      )}
    </Card>
  );
}
