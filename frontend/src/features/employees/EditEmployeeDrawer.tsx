import { Button, Drawer, Form } from "antd";
import { useEffect } from "react";

import type { Employee } from "../../api/employees";
import { showFieldErrors } from "../../lib/formErrors";
import { EmployeeFields } from "./EmployeeFields";
import { type DetailsValues, formValues } from "./employeeForm";
import { useReloadEmployee, useUpdateEmployee } from "./queries";
import { SaveError } from "./SaveError";

type Props = { employee: Employee; open: boolean; onClose: () => void };

export function EditEmployeeDrawer({ employee, open, onClose }: Props) {
  const [form] = Form.useForm<DetailsValues>();
  const update = useUpdateEmployee(employee);
  const reload = useReloadEmployee(employee.id);

  // A newer version from the server, such as the one Reload fetches after someone else saved
  // first, replaces whatever was typed: the form would otherwise keep typed values over it.
  useEffect(() => {
    form.resetFields();
  }, [employee.version, form]);

  function close() {
    update.reset();
    onClose();
  }

  function save(values: DetailsValues) {
    update.mutate(values, {
      onSuccess: close,
      onError: (error) => showFieldErrors(form, error),
    });
  }

  return (
    <Drawer
      title={`Edit ${employee.full_name}'s details`}
      open={open}
      onClose={close}
      width={480}
      destroyOnHidden
      extra={
        <Button type="primary" onClick={() => form.submit()} loading={update.isPending}>
          Save
        </Button>
      }
    >
      <SaveError
        error={update.error}
        onReload={() => {
          update.reset();
          void reload();
        }}
      />
      {/* Keyed on the version, so its initial values are always the latest record's. */}
      <Form
        key={employee.version}
        form={form}
        layout="vertical"
        initialValues={formValues(employee)}
        onFinish={save}
        disabled={update.isPending}
      >
        <EmployeeFields />
      </Form>
    </Drawer>
  );
}
