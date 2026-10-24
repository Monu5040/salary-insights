import { Card, Empty, Table, Tag, Typography } from "antd";

import type { Exploration, Group, Metric, Preset } from "../../api/insights";
import { ErrorAlert } from "../../components/ErrorAlert";
import { CardTitle } from "../../components/Titles";
import { Bars, RangeBars } from "./charts";
import { DIMENSIONS, METRICS } from "./labels";
import { useExplore } from "./queries";
import { withScope } from "./scope";
import { useCurrency } from "./useCurrency";
import { groupName, showValue } from "./values";

/** One of the dashboard's saved questions, drawn as bars, ranges or a table. */
export function PresetCard({ preset, scope }: { preset: Preset; scope: string }) {
  const answer = useExplore(withScope(scope, { metric: preset.metrics, by: preset.by }));
  return (
    <Card
      title={<CardTitle>{preset.title}</CardTitle>}
      loading={answer.isPending}
      style={{ height: "100%" }}
    >
      {answer.error && <ErrorAlert error={answer.error} onRetry={() => void answer.refetch()} />}
      {answer.data &&
        (answer.data.groups.length === 0 ? (
          <Empty description="Nobody matches these filters" />
        ) : (
          <Chart preset={preset} answer={answer.data} />
        ))}
    </Card>
  );
}

function Chart({ preset, answer }: { preset: Preset; answer: Exploration }) {
  const { money, compact } = useCurrency(answer.currency);
  const [metric] = preset.metrics;

  if (preset.chart === "ranges") {
    return (
      <RangeBars
        ranges={answer.groups.map((group) => ({
          key: groupName(group),
          label: groupName(group),
          p10: Number(group.values.p10),
          p25: Number(group.values.p25),
          median: Number(group.values.median),
          p75: Number(group.values.p75),
          p90: Number(group.values.p90),
          text: `median ${money(group.values.median ?? null)}`,
          lowSample: group.low_sample,
        }))}
      />
    );
  }
  if (preset.chart === "bars") {
    return (
      <Bars
        bars={answer.groups.map((group) => ({
          key: groupName(group),
          label: groupName(group),
          value: Number(group.values[metric]),
          text:
            metric === "headcount"
              ? showValue(metric, group.values[metric], money)
              : compact(group.values[metric] ?? null),
          note: `${group.headcount.toLocaleString("en")} people`,
        }))}
      />
    );
  }
  if (answer.by.length === 2) return <Pivot answer={answer} money={money} />;
  return <Ranking answer={answer} money={money} />;
}

type PivotProps = { answer: Exploration; money: (amount: string | null) => string };

/** One grouping with several measures, such as every job title: a table to sort and page
 *  through, since there can be dozens of groups. */
function Ranking({ answer, money }: PivotProps) {
  const [dimension] = answer.by;
  const number = (group: Group, metric: Metric) => Number(group.values[metric] ?? -Infinity);
  return (
    <Table<Group>
      size="small"
      rowKey={(group) => JSON.stringify(group.keys)}
      dataSource={answer.groups}
      scroll={{ x: true }}
      pagination={{ pageSize: 10, hideOnSinglePage: true, showSizeChanger: false }}
      columns={[
        {
          key: dimension,
          title: DIMENSIONS[dimension],
          sorter: (a, b) => groupName(a).localeCompare(groupName(b)),
          render: (_: unknown, group: Group) => (
            <span style={{ fontWeight: 500 }}>
              {groupName(group)}
              {group.low_sample && (
                <Tag bordered={false} style={{ marginLeft: 6 }}>
                  Under 5
                </Tag>
              )}
            </span>
          ),
        },
        ...answer.metrics.map((metric) => ({
          key: metric,
          title: METRICS[metric],
          align: "right" as const,
          sorter: (a: Group, b: Group) => number(a, metric) - number(b, metric),
          render: (_: unknown, group: Group) => showValue(metric, group.values[metric], money),
        })),
      ]}
    />
  );
}

type Cell = { text: string; share: number };
type PivotRow = { name: string; cells: Record<string, Cell> };

/** A cell's tint, from faint to the largest value's: dark text keeps 8:1 or more on all. */
const heat = (cell?: Cell) =>
  cell && { background: `rgba(79, 70, 229, ${(0.03 + 0.22 * cell.share).toFixed(3)})` };

/** Two groupings as rows and columns, such as countries by departments, larger values deeper. */
function Pivot({ answer, money }: PivotProps) {
  const [rows, columns] = answer.by;
  const [metric] = answer.metrics;
  const columnNames = [...new Set(answer.groups.map((group) => group.labels[columns] ?? ""))];
  const amount = (value?: string | null) => Math.max(Number(value ?? 0), 0);
  const largest = Math.max(0, ...answer.groups.map((group) => amount(group.values[metric]))) || 1;
  const byRow = new Map<string, Record<string, Cell>>();
  for (const group of answer.groups) {
    const name = group.labels[rows] ?? "";
    const cells = byRow.get(name) ?? {};
    const value = showValue(metric, group.values[metric], money);
    cells[group.labels[columns] ?? ""] = {
      text: group.low_sample ? `${value} *` : value,
      share: amount(group.values[metric]) / largest,
    };
    byRow.set(name, cells);
  }
  return (
    <>
      <Table<PivotRow>
        size="small"
        pagination={false}
        scroll={{ x: true }}
        rowKey="name"
        dataSource={[...byRow].map(([name, cells]) => ({ name, cells }))}
        columns={[
          {
            key: "name",
            dataIndex: "name",
            title: "",
            fixed: "left",
            render: (name: string) => <span style={{ fontWeight: 500 }}>{name}</span>,
          },
          ...columnNames.map((column) => ({
            key: column,
            title: column,
            align: "right" as const,
            render: (_: unknown, row: PivotRow) => row.cells[column]?.text ?? "",
            onCell: (row: PivotRow) => ({ style: heat(row.cells[column]) }),
          })),
        ]}
      />
      <Typography.Paragraph type="secondary" style={{ marginTop: 8, marginBottom: 0 }}>
        * fewer than 5 people
      </Typography.Paragraph>
    </>
  );
}
