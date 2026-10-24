import { Alert, Descriptions, Table, Tabs, Typography } from "antd";

import type { ImportPreview } from "../../api/imports";

const shown = (value: unknown) => (value === null || value === "" ? "none" : String(value));

/** What the file would change, before anything is changed (design §6). */
export function Preview({ preview }: { preview: ImportPreview }) {
  const errors = preview.error_rows;

  return (
    <>
      <Descriptions
        size="small"
        column={{ xs: 1, md: 3 }}
        items={[
          { label: "New employees", children: preview.creates },
          { label: "Changed", children: preview.changes },
          { label: "Unchanged", children: preview.unchanged },
          { label: "Rows with errors", children: errors },
          { label: "Rows in the file", children: preview.rows },
        ]}
      />
      {preview.ignored_columns.length > 0 && (
        <Typography.Paragraph type="secondary">
          Columns not imported: {preview.ignored_columns.join(", ")}.
        </Typography.Paragraph>
      )}
      {errors > 0 && (
        <Alert
          type="error"
          showIcon
          style={{ marginBottom: 16 }}
          message={`${errors} ${errors === 1 ? "row has" : "rows have"} errors`}
          description={
            "Fix them in the sheet and preview it again: " +
            "the file is imported whole or not at all."
          }
        />
      )}
      <Tabs
        defaultActiveKey={errors > 0 ? "errors" : "changes"}
        items={[
          {
            key: "errors",
            label: `Errors (${preview.row_errors.length})`,
            disabled: errors === 0,
            children: (
              <Table
                size="small"
                rowKey={(error) => `${error.line}-${error.column}`}
                dataSource={preview.row_errors}
                pagination={{ pageSize: 20, hideOnSinglePage: true }}
                columns={[
                  { key: "line", title: "Line", dataIndex: "line", width: 80 },
                  { key: "column", title: "Column", dataIndex: "column", width: 160 },
                  { key: "message", title: "Error", dataIndex: "message" },
                ]}
              />
            ),
          },
          {
            key: "changes",
            label: `Changes (${preview.changes})`,
            children: (
              <Table
                size="small"
                rowKey="line"
                dataSource={preview.changed_employees}
                pagination={{ pageSize: 20, hideOnSinglePage: true }}
                columns={[
                  { key: "code", title: "Code", dataIndex: "employee_code", width: 110 },
                  { key: "name", title: "Name", dataIndex: "full_name" },
                  {
                    key: "what",
                    title: "What changes",
                    render: (_, change) => (
                      <>
                        {Object.entries(change.fields).map(([field, [before, after]]) => (
                          <div key={field}>
                            {field.replace("_", " ")}: {shown(before)} → {shown(after)}
                          </div>
                        ))}
                        {change.salary && <div>salary: {change.salary}</div>}
                      </>
                    ),
                  },
                ]}
              />
            ),
          },
          {
            key: "creates",
            label: `New (${preview.creates})`,
            children: (
              <Table
                size="small"
                rowKey="line"
                dataSource={preview.new_employees}
                pagination={{ pageSize: 20, hideOnSinglePage: true }}
                columns={[
                  { key: "code", title: "Code", dataIndex: "employee_code", width: 110 },
                  { key: "name", title: "Name", dataIndex: "full_name" },
                  { key: "salary", title: "Starting salary", dataIndex: "salary" },
                ]}
              />
            ),
          },
        ]}
      />
    </>
  );
}
