import { Card, Flex, Select, Table, Tag, Typography } from "antd";
import { useSearchParams } from "react-router";

import type { Dimension, Group, Metric } from "../../api/insights";
import { ErrorAlert } from "../../components/ErrorAlert";
import { CardTitle } from "../../components/Titles";
import { DIMENSIONS, METRICS } from "./labels";
import { useExplore } from "./queries";
import { withScope } from "./scope";
import { useCurrency } from "./useCurrency";
import { showValue } from "./values";

const NOTHING = "";

/** Any question the dashboard doesn't ask: up to five measures, grouped by up to two things,
 *  with the page's filters (design §4 Explorer). Its choices live in the page address too. */
export function Explorer({ scope }: { scope: string }) {
  const [params, setParams] = useSearchParams();
  const chosen = params.getAll("metric");
  const metrics = (chosen.length ? chosen : ["median"]) as Metric[];
  const by = (params.has("by") ? params.getAll("by") : ["country"]).filter(Boolean) as Dimension[];
  const answer = useExplore(withScope(scope, { metric: metrics, by }));

  function choose(key: "metric" | "by", values: string[]) {
    const next = new URLSearchParams(params);
    next.delete(key);
    for (const value of values.length ? values : [NOTHING]) next.append(key, value);
    setParams(next);
  }

  const dimensions = (Object.keys(DIMENSIONS) as Dimension[]).map((value) => ({
    value,
    label: DIMENSIONS[value],
  }));

  return (
    <Card id="explorer" title={<CardTitle>Explore</CardTitle>}>
      <Flex gap={8} wrap style={{ marginBottom: 16 }}>
        <Select
          mode="multiple"
          aria-label="Measures"
          prefix={<Typography.Text type="secondary">Measures</Typography.Text>}
          virtual={false}
          maxCount={5}
          value={metrics}
          options={(Object.keys(METRICS) as Metric[]).map((value) => ({
            value,
            label: METRICS[value],
          }))}
          onChange={(values: string[]) => choose("metric", values.length ? values : ["median"])}
          style={{ minWidth: 300 }}
        />
        <Select
          mode="multiple"
          aria-label="Group by"
          prefix={<Typography.Text type="secondary">Group by</Typography.Text>}
          placeholder="Everyone together"
          virtual={false}
          maxCount={2}
          value={by}
          options={dimensions}
          onChange={(values: string[]) => choose("by", values)}
          style={{ minWidth: 300 }}
        />
      </Flex>
      {answer.error && <ErrorAlert error={answer.error} onRetry={() => void answer.refetch()} />}
      <GroupsTable
        groups={answer.data?.groups}
        currency={answer.data?.currency ?? "USD"}
        metrics={metrics}
        by={by}
        loading={answer.isFetching}
      />
    </Card>
  );
}

type TableProps = {
  groups: Group[] | undefined;
  currency: string;
  metrics: Metric[];
  by: Dimension[];
  loading?: boolean;
};

/** An explorer answer as a table: a row per group, a column per measure. */
export function GroupsTable({ groups, currency, metrics, by, loading = false }: TableProps) {
  const { money } = useCurrency(currency);
  return (
    <Table<Group>
      size="small"
      loading={loading}
      rowKey={(group) => JSON.stringify(group.keys)}
      dataSource={groups}
      scroll={{ x: true }}
      pagination={{ pageSize: 20, hideOnSinglePage: true }}
      columns={[
        ...by.map((name) => ({
          key: name,
          title: DIMENSIONS[name],
          render: (_: unknown, group: Group) => group.labels[name],
        })),
        {
          key: "n",
          title: "People",
          align: "right" as const,
          render: (_: unknown, group: Group) => (
            <>
              {group.headcount.toLocaleString("en")}
              {group.low_sample && (
                <Tag bordered={false} style={{ marginLeft: 6 }}>
                  Under 5
                </Tag>
              )}
            </>
          ),
        },
        ...metrics.map((metric) => ({
          key: metric,
          title: METRICS[metric],
          align: "right" as const,
          render: (_: unknown, group: Group) => showValue(metric, group.values[metric], money),
        })),
      ]}
    />
  );
}
