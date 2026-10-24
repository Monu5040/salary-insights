import { Alert, Form, Input, Modal, Segmented, Select, Typography } from "antd";

import type { Employee, Reason, SalaryHistory } from "../../api/employees";
import { showFieldErrors } from "../../lib/formErrors";
import { useReloadEmployee } from "../employees/queries";
import { SaveError } from "../employees/SaveError";
import { useConfig } from "../reference/hooks";
import { NEW_REASONS, REASONS } from "./labels";
import { inForceBefore, PERCENT, proposedAmount, signedPercent } from "./preview";
import { useRecordChange } from "./queries";
import { useCurrencyOptions, useMoney } from "./useMoney";

type Values = {
  mode: "amount" | "percent";
  effective_date: string;
  amount?: string;
  percent?: string;
  currency: string;
  reason: Reason;
  note?: string;
};

type Props = { employee: Employee; history: SalaryHistory; open: boolean; onClose: () => void };

/** Record a raise or other change, past or future, with a preview of exactly what will be
 *  saved (design §6). A % is turned into the amount here; only the amount is sent. */
export function RecordChangeModal({ employee, history, open, onClose }: Props) {
  const [form] = Form.useForm<Values>();
  const today = useConfig().data?.today ?? "";
  const currencies = useCurrencyOptions();
  const money = useMoney(employee.country.code);
  const record = useRecordChange(employee);
  const reload = useReloadEmployee(employee.id);

  const mode = Form.useWatch("mode", form) ?? "percent";
  const day = Form.useWatch("effective_date", form) ?? "";
  const amount = Form.useWatch("amount", form);
  const percent = Form.useWatch("percent", form);
  const currency = Form.useWatch("currency", form);

  const current =
    history.records.find((row) => row.id === history.current_id) ?? history.records.at(-1);
  const before = day ? inForceBefore(history.records, day) : undefined;
  const sameCurrency = before !== undefined && currency === before.currency;
  const decimals = money.decimals(currency ?? "");
  const proposed = currency
    ? proposedAmount(mode, { amount, percent, currency }, before, decimals)
    : undefined;

  function close() {
    record.reset();
    onClose();
  }

  function save(values: Values) {
    if (!proposed) return;
    record.mutate(
      {
        effective_date: values.effective_date,
        amount: proposed,
        currency: values.currency,
        reason: values.reason,
        note: values.note ?? "",
      },
      {
        onSuccess: close,
        // In % mode the amount isn't on screen: its error belongs under the %.
        onError: (error) =>
          showFieldErrors(form, error, mode === "percent" ? { amount: "percent" } : {}),
      },
    );
  }

  return (
    <Modal
      title="Record a salary change"
      open={open}
      onCancel={close}
      okText="Save change"
      okButtonProps={{ disabled: !proposed, loading: record.isPending }}
      onOk={() => form.submit()}
      destroyOnHidden
    >
      <SaveError
        error={record.error}
        onReload={() => {
          record.reset();
          void reload();
        }}
      />
      <Form<Values>
        form={form}
        layout="vertical"
        onFinish={save}
        initialValues={{
          mode: "percent",
          effective_date: today,
          currency: current?.currency,
          reason: "merit",
        }}
      >
        <Form.Item label="Takes effect on" name="effective_date" rules={[{ required: true }]}>
          <Input type="date" />
        </Form.Item>
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
            label="New salary (a year)"
            name="amount"
            rules={[
              { required: true, message: "Enter the new salary" },
              {
                validator: (_, value?: string) =>
                  !value || proposedAmount("amount", { amount: value, currency }, before, decimals)
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
              if (before && code !== before.currency) form.setFieldValue("mode", "amount");
            }}
          />
        </Form.Item>
        <Form.Item label="Reason" name="reason" rules={[{ required: true }]}>
          <Select
            virtual={false}
            options={NEW_REASONS.map((value) => ({ value, label: REASONS[value] }))}
          />
        </Form.Item>
        <Form.Item label="Note" name="note">
          <Input.TextArea rows={2} maxLength={500} />
        </Form.Item>
      </Form>
      {proposed && currency && (
        <Alert
          type="info"
          showIcon
          message={
            before
              ? `${money.show(before.amount, before.currency)} → ` +
                `${money.show(proposed, currency)} ` +
                (sameCurrency
                  ? `(${signedPercent(before.amount, proposed)})`
                  : "(a currency change, not counted as a raise)")
              : `${money.show(proposed, currency)} from ${day}`
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
