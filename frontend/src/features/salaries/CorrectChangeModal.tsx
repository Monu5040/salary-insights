import { Form, Input, Modal, Select } from "antd";
import { useEffect } from "react";

import type { Employee, Reason, SalaryHistory, SalaryRow } from "../../api/employees";
import { showFieldErrors } from "../../lib/formErrors";
import { isAmount } from "../../lib/money";
import { useReloadEmployee } from "../employees/queries";
import { SaveError } from "../employees/SaveError";
import { NEW_REASONS, REASONS } from "./labels";
import { useCorrectChange } from "./queries";
import { useCurrencyOptions, useMoney } from "./useMoney";

type Values = {
  effective_date: string;
  amount: string;
  currency: string;
  reason: Reason;
  note: string;
};

type Props = {
  employee: Employee;
  history: SalaryHistory;
  change: SalaryRow | null;
  onClose: () => void;
};

/** Fix a wrong entry. The starting salary keeps its date and reason (edge case #45). */
export function CorrectChangeModal({ employee, history, change, onClose }: Props) {
  const [form] = Form.useForm<Values>();
  const currencies = useCurrencyOptions();
  const money = useMoney(employee.country.code);
  const correct = useCorrectChange(employee);
  const reload = useReloadEmployee(employee.id);
  const currency = Form.useWatch("currency", form) ?? "";
  // The entry as the server has it now: after a Reload, someone else's correction.
  const entry = change && (history.records.find((row) => row.id === change.id) ?? change);
  const hire = entry?.reason === "hire";

  // A newer version, such as the one Reload fetches after someone else saved first, replaces
  // whatever was typed, as in the employee's edit drawer.
  useEffect(() => {
    form.resetFields();
  }, [history.employee_version, form]);

  function close() {
    correct.reset();
    onClose();
  }

  return (
    <Modal
      title="Correct a salary change"
      open={change !== null}
      onCancel={close}
      okText="Save correction"
      okButtonProps={{ loading: correct.isPending }}
      onOk={() => form.submit()}
      destroyOnHidden
    >
      <SaveError
        error={correct.error}
        onReload={() => {
          correct.reset();
          void reload();
        }}
      />
      {entry && (
        <Form<Values>
          key={history.employee_version}
          form={form}
          layout="vertical"
          initialValues={entry}
          onFinish={(values) =>
            correct.mutate(
              { id: entry.id, input: values },
              { onSuccess: close, onError: (error) => showFieldErrors(form, error) },
            )
          }
        >
          <Form.Item
            label="Takes effect on"
            name="effective_date"
            rules={[{ required: true }]}
            extra={
              hire ? "The starting salary is dated on the hire date: change that instead." : ""
            }
          >
            <Input type="date" disabled={hire} />
          </Form.Item>
          <Form.Item
            label="Salary (a year)"
            name="amount"
            rules={[
              { required: true, message: "Enter the salary" },
              {
                validator: (_, value?: string) =>
                  !value || isAmount(value, money.decimals(currency))
                    ? Promise.resolve()
                    : Promise.reject(new Error(`At most ${money.decimals(currency)} decimals`)),
              },
            ]}
          >
            <Input inputMode="decimal" />
          </Form.Item>
          <Form.Item label="Currency" name="currency" rules={[{ required: true }]}>
            <Select showSearch virtual={false} options={currencies} />
          </Form.Item>
          <Form.Item label="Reason" name="reason" rules={[{ required: true }]}>
            <Select
              virtual={false}
              disabled={hire}
              options={(hire ? (["hire"] as Reason[]) : NEW_REASONS).map((value) => ({
                value,
                label: REASONS[value],
              }))}
            />
          </Form.Item>
          <Form.Item label="Note" name="note">
            <Input.TextArea rows={2} maxLength={500} />
          </Form.Item>
        </Form>
      )}
    </Modal>
  );
}
