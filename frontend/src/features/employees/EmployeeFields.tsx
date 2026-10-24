import { Alert, Form, Input, Select } from "antd";

import type { NewEmployeeInput } from "../../api/employees";
import { useCountries, useDepartments } from "../reference/hooks";
import { useCurrencyOptions } from "../salaries/useMoney";

const required = (message: string) => [{ required: true, message }];

/** The employee form's fields, shared by "add" and "edit". "Add" also asks for a salary. */
export function EmployeeFields({ withSalary = false }: { withSalary?: boolean }) {
  const countries = useCountries().data ?? [];
  const departments = useDepartments().data ?? [];
  const currencies = useCurrencyOptions();
  const form = Form.useFormInstance<NewEmployeeInput>();
  const countryCode = Form.useWatch("country", form);
  const currency = Form.useWatch("currency", form);
  const country = countries.find((row) => row.code === countryCode);

  return (
    <>
      <Form.Item label="Employee code" name="employee_code" rules={required("Enter the code")}>
        <Input />
      </Form.Item>
      <Form.Item label="Full name" name="full_name" rules={required("Enter the name")}>
        <Input />
      </Form.Item>
      <Form.Item
        label="Work email"
        name="email"
        rules={[
          ...required("Enter the work email"),
          { type: "email", message: "Enter an email address" },
        ]}
      >
        <Input />
      </Form.Item>
      <Form.Item label="Country" name="country" rules={required("Choose a country")}>
        <Select
          showSearch
          optionFilterProp="label"
          virtual={false}
          options={countries.map((row) => ({ value: row.code, label: row.name }))}
        />
      </Form.Item>
      <Form.Item label="Department" name="department" rules={required("Choose a department")}>
        <Select
          showSearch
          optionFilterProp="label"
          virtual={false}
          options={departments.map((row) => ({ value: row.id, label: row.name }))}
        />
      </Form.Item>
      <Form.Item label="Job title" name="job_title" rules={required("Enter the job title")}>
        <Input />
      </Form.Item>
      <Form.Item label="Hire date" name="hire_date" rules={required("Enter the hire date")}>
        <Input type="date" />
      </Form.Item>
      {withSalary && (
        <>
          <Form.Item
            label="Annual base salary"
            name="salary"
            rules={[
              ...required("Enter the salary"),
              { pattern: /^\d+(\.\d+)?$/, message: "Enter a plain number such as 85000.50" },
            ]}
          >
            <Input inputMode="decimal" />
          </Form.Item>
          <Form.Item label="Currency" name="currency" rules={required("Choose one")}>
            <Select showSearch virtual={false} options={currencies} />
          </Form.Item>
          {country && currency && currency !== country.default_currency && (
            // Allowed, but worth a second look (edge case #5).
            <Alert
              type="info"
              showIcon
              style={{ marginBottom: 24, gridColumn: "1 / -1" }}
              message={`Paid in ${currency}, not ${country.default_currency}, the usual currency in ${country.name}.`}
            />
          )}
        </>
      )}
    </>
  );
}
