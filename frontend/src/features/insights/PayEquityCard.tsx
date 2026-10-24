import { Card, Table, Typography } from "antd";
import { useState } from "react";
import { Link } from "react-router";

import type { Outlier } from "../../api/insights";
import { ErrorAlert } from "../../components/ErrorAlert";
import { CardTitle } from "../../components/Titles";
import { usePayEquity } from "./queries";
import { withScope } from "./scope";
import { useCurrency } from "./useCurrency";

const PAGE_SIZE = 10;

const percent = (ratio: string) => `${Math.round(Number(ratio) * 100)}%`;

/** Equal pay for equal work, without gender (requirements): people paid far from others with
 *  the same job title, furthest out first (design §4 Pay equity). */
export function PayEquityCard({ scope }: { scope: string }) {
  const [page, setPage] = useState(1);
  const answer = usePayEquity(
    withScope(scope, { page: [String(page)], page_size: [String(PAGE_SIZE)] }),
  );
  const { money } = useCurrency(answer.data?.currency ?? "USD");
  const band = answer.data?.band;

  return (
    <Card title={<CardTitle>Pay equity</CardTitle>}>
      <Typography.Paragraph type="secondary">
        {band
          ? `People paid below ${percent(band[0])} or above ${percent(band[1])} of the median`
          : "People paid far from the median"}{" "}
        of others with the same job title, in their country when at least 5 share it. Each is
        worth a look; a gap may have a good reason.
      </Typography.Paragraph>
      {answer.error && <ErrorAlert error={answer.error} onRetry={() => void answer.refetch()} />}
      <Table<Outlier>
        size="small"
        rowKey="id"
        loading={answer.isFetching}
        dataSource={answer.data?.results}
        scroll={{ x: true }}
        locale={{ emptyText: answer.data ? "Nobody is paid outside the band." : " " }}
        pagination={{
          current: page,
          pageSize: PAGE_SIZE,
          total: answer.data?.count ?? 0,
          hideOnSinglePage: true,
          showSizeChanger: false,
          onChange: setPage,
        }}
        columns={[
          {
            key: "name",
            title: "Employee",
            render: (_, row) => <Link to={`/employees/${row.id}`}>{row.full_name}</Link>,
          },
          { key: "title", title: "Job title", dataIndex: "job_title" },
          { key: "country", title: "Country", dataIndex: "country_name" },
          { key: "pay", title: "Salary", align: "right", render: (_, row) => money(row.pay) },
          {
            key: "median",
            title: "Peer median",
            align: "right",
            render: (_, row) => money(row.peer_median),
          },
          {
            key: "ratio",
            title: "Of the median",
            align: "right",
            render: (_, row) => percent(row.compa_ratio),
          },
          {
            key: "peers",
            title: "Compared with",
            render: (_, row) => `${row.peers} people: ${row.definition.toLowerCase()}`,
          },
        ]}
      />
    </Card>
  );
}
