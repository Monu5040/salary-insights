import { InboxOutlined } from "@ant-design/icons";
import { Alert, Button, Card, Form, Popconfirm, Radio, Result, Space, Upload } from "antd";
import { useState } from "react";
import { Link } from "react-router";

import type { Applied, DateFormat, ImportPreview } from "../../api/imports";
import { HttpError } from "../../api/http";
import { ErrorAlert } from "../../components/ErrorAlert";
import { PageHeader } from "../../components/PageHeader";
import { CardTitle } from "../../components/Titles";
import { radioGroup } from "../../lib/a11y";
import { Preview } from "./Preview";
import { useApply, usePreview } from "./queries";

const DATE_LABEL = "Dates that aren't YYYY-MM-DD are written";

/** Choose a sheet → preview what it changes → apply it whole (design §6). Nothing is stored
 *  between the steps: apply sends the file again with the preview's fingerprint. */
export function ImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [dateFormat, setDateFormat] = useState<DateFormat>("iso");
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [changed, setChanged] = useState(false);
  const [applied, setApplied] = useState<Applied | null>(null);
  const check = usePreview();
  const apply = useApply();

  function again() {
    setFile(null);
    setPreview(null);
    setApplied(null);
    setChanged(false);
    check.reset();
    apply.reset();
  }

  function runPreview() {
    if (!file) return;
    setChanged(false);
    apply.reset();
    check.mutate({ file, dateFormat }, { onSuccess: setPreview });
  }

  function runApply() {
    if (!file || !preview) return;
    apply.mutate(
      { file, dateFormat, fingerprint: preview.fingerprint },
      {
        onSuccess: setApplied,
        onError: (error) => {
          // Someone changed an employee in the file since: here is the plan as it is now.
          const fresh = error instanceof HttpError ? error.problem?.preview : undefined;
          if (error instanceof HttpError && error.status === 409 && fresh) {
            setPreview(fresh as ImportPreview);
            setChanged(true);
            apply.reset();
          }
        },
      },
    );
  }

  return (
    <>
      <PageHeader
        title="Import from Excel"
        subtitle="Add or update employees from a spreadsheet: nothing changes until you apply it"
      />
      {applied ? (
        <Card>
          <Result
            status="success"
            title={`Imported ${file?.name ?? "the file"}`}
            subTitle={
              `${applied.creates} new employees, ${applied.changes} changed, ` +
              `${applied.unchanged} unchanged.`
            }
            extra={
              <Space>
                <Link to="/employees">
                  <Button type="primary">See employees</Button>
                </Link>
                <Button onClick={again}>Import another file</Button>
              </Space>
            }
          />
        </Card>
      ) : (
        <>
          <Card style={{ marginBottom: 16 }}>
            <Form layout="vertical">
              <Form.Item>
                <Upload.Dragger
                  accept=".csv,text/csv"
                  maxCount={1}
                  fileList={file ? [{ uid: "file", name: file.name, status: "done" }] : []}
                  beforeUpload={(chosen) => {
                    setFile(chosen);
                    setPreview(null);
                    return false; // sent with the button below, not straight away
                  }}
                  onRemove={again}
                >
                  <p className="ant-upload-drag-icon">
                    <InboxOutlined aria-hidden />
                  </p>
                  <p className="ant-upload-text">Click or drag a CSV file here</p>
                  <p className="ant-upload-hint">
                    In Excel choose Save As, then CSV UTF-8. Up to 10 MB and 50,000 rows. The
                    directory's Export CSV gives the columns.
                  </p>
                </Upload.Dragger>
              </Form.Item>
              <Form.Item label={DATE_LABEL}>
                <Radio.Group
                  {...radioGroup(DATE_LABEL)}
                  value={dateFormat}
                  onChange={(event) => {
                    setDateFormat(event.target.value as DateFormat);
                    setPreview(null);
                  }}
                  options={[
                    { value: "iso", label: "Only as YYYY-MM-DD" },
                    { value: "dmy", label: "Day first (31/12/2026)" },
                    { value: "mdy", label: "Month first (12/31/2026)" },
                  ]}
                />
              </Form.Item>
              {check.error && <ErrorAlert error={check.error} />}
              <Button
                type="primary"
                disabled={!file}
                loading={check.isPending}
                onClick={runPreview}
              >
                Preview
              </Button>
            </Form>
          </Card>
          {preview && (
            <Card title={<CardTitle>{`What ${file?.name ?? "the file"} changes`}</CardTitle>}>
              {changed && (
                <Alert
                  type="warning"
                  showIcon
                  style={{ marginBottom: 16 }}
                  message="Some employees in this file changed after the preview."
                  description="This is the preview as it is now. Check it, then apply again."
                />
              )}
              <Preview preview={preview} />
              {apply.error && <ErrorAlert error={apply.error} />}
              <Popconfirm
                title="Apply this file?"
                description="Every change is applied together, or none is."
                okText="Apply"
                onConfirm={runApply}
                disabled={preview.error_rows > 0}
              >
                <Button
                  type="primary"
                  style={{ marginTop: 16 }}
                  disabled={preview.error_rows > 0 || preview.creates + preview.changes === 0}
                  loading={apply.isPending}
                >
                  Apply
                </Button>
              </Popconfirm>
            </Card>
          )}
        </>
      )}
    </>
  );
}
