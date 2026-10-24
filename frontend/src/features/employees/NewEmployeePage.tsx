import { Alert, Button, Card, Form } from "antd";
import { Link, useNavigate } from "react-router";

import type { EmployeeInput } from "../../api/employees";
import { HttpError } from "../../api/http";
import { ErrorAlert } from "../../components/ErrorAlert";
import { PageHeader } from "../../components/PageHeader";
import { showFieldErrors } from "../../lib/formErrors";
import { useCountries } from "../reference/hooks";
import { EmployeeFields } from "./EmployeeFields";
import { useCreateEmployee } from "./queries";

export function NewEmployeePage() {
  const [form] = Form.useForm<EmployeeInput>();
  const create = useCreateEmployee();
  const navigate = useNavigate();
  const countries = useCountries().data ?? [];
  const problem = create.error instanceof HttpError ? create.error.problem : undefined;

  function save(values: EmployeeInput) {
    create.mutate(values, {
      onSuccess: (employee) => void navigate(`/employees/${employee.id}`),
      onError: (error) => showFieldErrors(form, error),
    });
  }

  return (
    <>
      <PageHeader
        title="Add an employee"
        subtitle="A full-time employee and their annual gross base salary"
        breadcrumb={[
          { title: <Link to="/employees">Employees</Link> },
          { title: "Add an employee" },
        ]}
      />
      <Card style={{ maxWidth: 760 }}>
        {create.error &&
          (problem?.existing_id ? (
            // Someone already has this code or email: offer to open them (edge case #10).
            <Alert
              type="warning"
              showIcon
              style={{ marginBottom: 16 }}
              message={create.error.message}
              action={<Link to={`/employees/${problem.existing_id}`}>Open that employee</Link>}
            />
          ) : (
            <ErrorAlert error={create.error} />
          ))}
        <Form<EmployeeInput>
          form={form}
          layout="vertical"
          onFinish={save}
          onValuesChange={(changed: Partial<EmployeeInput>) => {
            // Until someone picks a currency, use the new country's usual one.
            const country = countries.find((row) => row.code === changed.country);
            if (country && !form.isFieldTouched("currency")) {
              form.setFieldValue("currency", country.default_currency);
            }
          }}
        >
          {/* Two fields a row where there is room for them. */}
          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
              columnGap: 16,
            }}
          >
            <EmployeeFields withSalary />
          </div>
          <Button type="primary" htmlType="submit" loading={create.isPending}>
            Add employee
          </Button>
        </Form>
      </Card>
    </>
  );
}
