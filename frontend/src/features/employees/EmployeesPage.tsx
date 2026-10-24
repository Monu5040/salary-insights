import { useQueryClient } from "@tanstack/react-query";
import { PlusOutlined } from "@ant-design/icons";
import { Button, Card, Empty, Flex, Input, Table, type TableColumnsType } from "antd";
import type { SorterResult } from "antd/es/table/interface";
import { Link, useNavigate, useSearchParams } from "react-router";

import { DIRECTORY_PARAMS, type EmployeeRow } from "../../api/employees";
import { ErrorAlert } from "../../components/ErrorAlert";
import { PageHeader } from "../../components/PageHeader";
import { PersonAvatar } from "../../components/PersonAvatar";
import { Toolbar } from "../../components/Toolbar";
import { formatDate } from "../../lib/format";
import { ReferenceFilters } from "../reference/ReferenceFilters";
import { employeeQuery, useDirectory } from "./queries";
import { useMoney } from "../salaries/useMoney";

type Changes = Record<string, string | string[] | undefined>;

/** The parameters that narrow the list, as against those that order and page it. */
const NARROWING = ["q", "country", "department"];

/** The directory's API query: the page address's own parameters, in a stable order. */
function directoryQuery(params: URLSearchParams): string {
  const query = new URLSearchParams();
  for (const key of DIRECTORY_PARAMS) {
    for (const value of params.getAll(key)) query.append(key, value);
  }
  return query.toString();
}

export function EmployeesPage() {
  const [params, setParams] = useSearchParams();
  const directory = useDirectory(directoryQuery(params));
  const navigate = useNavigate();
  const client = useQueryClient();
  const sort = params.get("sort") ?? "full_name";
  const narrowed = NARROWING.some((key) => params.has(key));

  /** Filters, sort and page live in the address, so a view can be shared (design §8). */
  function update(changes: Changes, keepPage = false) {
    const next = new URLSearchParams(params);
    for (const [key, value] of Object.entries(changes)) {
      next.delete(key);
      for (const item of [value ?? []].flat()) next.append(key, item);
    }
    if (!keepPage) next.delete("page");
    setParams(next);
  }

  const sortable = (key: string) => ({
    key,
    sorter: true,
    sortOrder:
      sort === key ? ("ascend" as const) : sort === `-${key}` ? ("descend" as const) : null,
  });

  const columns: TableColumnsType<EmployeeRow> = [
    { ...sortable("employee_code"), title: "Code", dataIndex: "employee_code" },
    {
      ...sortable("full_name"),
      title: "Name",
      render: (_, row) => (
        <Flex align="center" gap={10}>
          <PersonAvatar name={row.full_name} size={30} />
          <Link to={`/employees/${row.id}`}>{row.full_name}</Link>
        </Flex>
      ),
    },
    { ...sortable("country"), title: "Country", render: (_, row) => row.country.name },
    { ...sortable("department"), title: "Department", render: (_, row) => row.department.name },
    { ...sortable("job_title"), title: "Job title", dataIndex: "job_title" },
    { ...sortable("hire_date"), title: "Hired", render: (_, row) => formatDate(row.hire_date) },
    {
      key: "salary",
      title: "Annual salary",
      align: "right",
      render: (_, row) => <Salary row={row} />,
    },
  ];

  return (
    <>
      <PageHeader
        title="Employees"
        subtitle="Everyone at ACME and their annual base salary"
        extra={
          <Button
            type="primary"
            icon={<PlusOutlined aria-hidden />}
            onClick={() => void navigate("/employees/new")}
          >
            Add employee
          </Button>
        }
      />
      <Filters params={params} onChange={update} />
      {directory.error && (
        <ErrorAlert error={directory.error} onRetry={() => void directory.refetch()} />
      )}
      <Card styles={{ body: { padding: 0 } }}>
        <Table<EmployeeRow>
          rowKey="id"
          size="middle"
          columns={columns}
          dataSource={directory.data?.results}
          loading={directory.isFetching}
          scroll={{ x: true }}
          locale={{
            // Nothing to say while loading, or after a failure: the alert above says why.
            emptyText: directory.data ? (
              <EmptyDirectory
                narrowed={narrowed}
                onClear={() => update(Object.fromEntries(NARROWING.map((key) => [key, undefined])))}
              />
            ) : (
              <span />
            ),
          }}
          pagination={{
            current: directory.data?.page ?? 1,
            pageSize: directory.data?.page_size ?? 25,
            total: directory.data?.count ?? 0,
            showSizeChanger: true,
            pageSizeOptions: [25, 50, 100, 200],
            showTotal: (total) => `${total.toLocaleString("en")} employees`,
            style: { paddingInline: 16 },
          }}
          onChange={(pagination, _filters, sorter, { action }) => {
            if (action === "paginate") {
              const page = String(pagination.current ?? 1);
              update({ page, page_size: String(pagination.pageSize ?? 25) }, true);
            } else if (action === "sort") {
              const { columnKey, order } = sorter as SorterResult<EmployeeRow>;
              const key = String(columnKey);
              update({ sort: order ? (order === "descend" ? `-${key}` : key) : undefined });
            }
          }}
          onRow={(row) => ({
            // Start loading the record while the pointer is on its row (design §8).
            onMouseEnter: () => void client.prefetchQuery(employeeQuery(row.id)),
          })}
        />
      </Card>
    </>
  );
}

function EmptyDirectory({ narrowed, onClear }: { narrowed: boolean; onClear: () => void }) {
  if (!narrowed) return <Empty description="No employees yet" />;
  return (
    <Empty description="No employees match these filters">
      <Button onClick={onClear}>Clear filters</Button>
    </Empty>
  );
}

type FiltersProps = { params: URLSearchParams; onChange: (changes: Changes) => void };

function Filters({ params, onChange }: FiltersProps) {
  const search = params.get("q") ?? "";

  return (
    <Toolbar>
      <Input.Search
        key={search}
        defaultValue={search}
        placeholder="Name or employee code"
        aria-label="Search employees"
        allowClear
        enterButton
        onSearch={(value) => onChange({ q: value.trim() || undefined })}
        style={{ width: 300 }}
      />
      <ReferenceFilters params={params} onChange={onChange} />
    </Toolbar>
  );
}

/** A salary in its own currency, written the way the employee's country writes it. */
function Salary({ row }: { row: EmployeeRow }) {
  const money = useMoney(row.country.code);
  return (
    <span style={{ fontVariantNumeric: "tabular-nums" }}>
      {money.show(row.salary, row.currency)}
    </span>
  );
}
