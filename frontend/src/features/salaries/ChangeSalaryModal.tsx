import { Alert, Form, Input, Modal, Segmented, Select, Typography } from "antd";

import type { Employee } from "../../api/employees";
import { showFieldErrors } from "../../lib/formErrors";
import { useReloadEmployee, useUpdateEmployee } from "../employees/queries";
import { SaveError } from "../employees/SaveError";
import { PERCENT, proposedAmount, signedPercent } from "./preview";
import { useCurrencyOptions, useMoney } from "./useMoney";

type Values = {
  mode: "amount" | "percent";
  amount?: string;
  percent?: string;
  currency: string;
};

type Props = { employee: Employee; open: boolean; onClose: () => void };

/** Change the current salary, with a preview of exactly what will be saved (design §6).
 *  A % is turned into the amount here; only the amount is sent. */
export function ChangeSalaryModal({ employee, open, onClose }: Props) {
  const [form] = Form.useForm<Values>();
  const currencies = useCurrencyOptions();
  const money = useMoney(employee.country.code);
  const update = useUpdateEmployee(employee);
  const reload = useReloadEmployee(employee.id);

  const mode = Form.useWatch("mode", form) ?? "percent";
  const amount = Form.useWatch("amount", form);
  const percent = Form.useWatch("percent", form);
  const currency = Form.useWatch("currency", form) ?? employee.currency;

  // A % only makes sense in the same currency: a new currency needs its amount typed.
  const sameCurrency = currency === employee.currency;
  const decimals = money.decimals(currency);
  const proposed = proposedAmount(
    sameCurrency ? mode : "amount",
    { amount, percent },
    employee.salary,
    decimals,
  );

  function close() {
    update.reset();
    form.resetFields();
    onClose();
  }

  function save(values: Values) {
    if (!proposed) return;
    update.mutate(
      { salary: proposed, currency: values.currency },
      {
        onSuccess: close,
        // In % mode the amount isn't on screen: its error belongs under the %.
        onError: (error) =>
          showFieldErrors(form, error, mode === "percent" ? { salary: "percent" } : {}),
      },
    );
  }

  return (
    <Modal
      title="Change salary"
      open={open}
      onCancel={close}
      okText="Save salary"
      okButtonProps={{ disabled: !proposed, loading: update.isPending }}
      onOk={() => form.submit()}
      destroyOnHidden
    >
      <SaveError
        error={update.error}
        onReload={() => {
          update.reset();
          void reload();
        }}
      />
      <Form<Values>
        form={form}
        layout="vertical"
        onFinish={save}
        initialValues={{ mode: "percent", currency: employee.currency }}
      >
        <Form.Item name="mode">
          <Segmented
            options={[
              { value: "percent", label: "Raise by %", disabled: !sameCurrency },
              { value: "amount", label: "New amount" },
            ]}
          />
        </Form.Item>
        {mode === "percent" && sameCurrency ? (
          <Form.Item
            label="Raise (%)"
            name="percent"
            rules={[
              { required: true, message: "Enter the % change, such as 7 or -2.5" },
              { pattern: PERCENT, message: "Enter a number such as 7 or -2.5" },
            ]}
          >
            <Input inputMode="decimal" suffix="%" />
          </Form.Item>
        ) : (
          <Form.Item
            label="New annual salary"
            name="amount"
            rules={[
              { required: true, message: "Enter the new salary" },
              {
                validator: (_, value?: string) =>
                  !value || proposedAmount("amount", { amount: value }, employee.salary, decimals)
                    ? Promise.resolve()
                    : Promise.reject(new Error(`A number above 0, at most ${decimals} decimals`)),
              },
            ]}
          >
            <Input inputMode="decimal" />
          </Form.Item>
        )}
        <Form.Item label="Currency" name="currency" rules={[{ required: true }]}>
          <Select
            showSearch
            virtual={false}
            options={currencies}
            onChange={(code: string) => {
              if (code !== employee.currency) form.setFieldValue("mode", "amount");
            }}
          />
        </Form.Item>
      </Form>
      {proposed && (
        <Alert
          type="info"
          showIcon
          message={
            `${money.show(employee.salary, employee.currency)} → ` +
            `${money.show(proposed, currency)} ` +
            (sameCurrency
              ? `(${signedPercent(employee.salary, proposed)})`
              : "(a change of currency)")
          }
          description={
            <Typography.Text type="secondary">
              This exact amount is what will be saved.
            </Typography.Text>
          }
        />
      )}
    </Modal>
  );
}
