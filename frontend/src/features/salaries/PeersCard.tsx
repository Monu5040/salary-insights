import { Card, Flex, Tag, theme, Typography } from "antd";

import type { Employee, PeerPosition } from "../../api/employees";
import { HttpError } from "../../api/http";
import { ErrorAlert } from "../../components/ErrorAlert";
import { Facts } from "../../components/Facts";
import { CardTitle } from "../../components/Titles";
import { usePeers } from "../employees/queries";
import { useMoney } from "./useMoney";

/** Where the employee's salary sits among colleagues with the same job title (design §4). */
export function PeersCard({ employee }: { employee: Employee }) {
  const peers = usePeers(employee.id);
  const money = useMoney(employee.country.code);
  const position = peers.data;
  const show = (amount: string | null) =>
    amount === null || !position ? "" : money.show(amount, position.currency);
  const range = (from: string | null, to: string | null) => `${show(from)} – ${show(to)}`;
  const rank = position?.percentile_rank ?? null;

  return (
    <Card
      title={<CardTitle>Among peers</CardTitle>}
      style={{ marginBottom: 16 }}
      loading={peers.isPending}
    >
      {peers.error &&
        (peers.error instanceof HttpError && peers.error.status === 404 ? (
          // Someone whose first salary starts later has nothing to compare yet.
          <Typography.Text type="secondary">{peers.error.message}</Typography.Text>
        ) : (
          <ErrorAlert error={peers.error} onRetry={() => void peers.refetch()} />
        ))}
      {position && (
        <>
          <Typography.Paragraph style={{ marginBottom: 8 }}>
            {position.definition}: {position.peers} {position.peers === 1 ? "person" : "people"}
          </Typography.Paragraph>
          {position.low_sample && (
            <Tag bordered={false} color="gold" style={{ marginBottom: 8 }}>
              Fewer than 5: read with care
            </Tag>
          )}
          {position.p10 !== null && <RangeBar position={position} />}
          <Facts
            width={150}
            items={[
              { label: "Salary", value: show(position.pay) },
              { label: "Peer median", value: show(position.median) || "No peers" },
              { label: "Paid more than", value: rank === null ? "" : `${rank}% of peers` },
              { label: "Compa-ratio (salary ÷ median)", value: position.compa_ratio ?? "" },
              { label: "Middle half of peers", value: range(position.p25, position.p75) },
              { label: "Peers from P10 to P90", value: range(position.p10, position.p90) },
            ]}
          />
          <Typography.Paragraph type="secondary" style={{ margin: "16px 0 0", fontSize: 12 }}>
            Amounts in {position.currency}, converted at the fixed budget exchange rates.
          </Typography.Paragraph>
        </>
      )}
    </Card>
  );
}

/** P10 to P90 as a bar, the middle half darker, the median as a line and this person as a dot. */
function RangeBar({ position }: { position: PeerPosition }) {
  const { token } = theme.useToken();
  const [whisker, middleHalf, medianLine] = [
    token.colorBorder,
    token.colorPrimaryBorder,
    token.colorPrimaryActive,
  ];
  const dot = token.orange6;
  const points = [position.p10, position.p90, position.pay].filter((value) => value !== null);
  const numbers = points.map(Number); // for drawing only: pixels don't need exact decimals
  const low = Math.min(...numbers);
  const span = Math.max(...numbers) - low || 1;
  const at = (value: string | null) => `${((Number(value) - low) / span) * 100}%`;
  const bar = (top: number, height: number, background: string) =>
    ({ position: "absolute", top, height, background, borderRadius: height }) as const;
  const between = (from: string | null, to: string | null) => ({
    left: at(from),
    width: `calc(${at(to)} - ${at(from)})`,
  });
  const key = (background: string, width: number, height: number) => (
    <span style={{ display: "inline-block", width, height, background, borderRadius: height }} />
  );

  return (
    <div aria-hidden style={{ margin: "8px 0 20px" }}>
      <div style={{ position: "relative", height: 28, margin: "0 8px" }}>
        <div style={{ ...bar(12, 4, whisker), ...between(position.p10, position.p90) }} />
        <div style={{ ...bar(7, 14, middleHalf), ...between(position.p25, position.p75) }} />
        <div style={{ ...bar(3, 22, medianLine), width: 3, left: at(position.median) }} />
        <div
          style={{
            position: "absolute",
            top: 7,
            width: 14,
            height: 14,
            marginLeft: -7,
            borderRadius: "50%",
            background: dot,
            border: `2px solid ${token.colorBgContainer}`,
            boxShadow: `0 0 0 1px ${dot}`,
            left: at(position.pay),
          }}
        />
      </div>
      <Flex gap={16} wrap style={{ marginTop: 6, fontSize: 12, color: token.colorTextSecondary }}>
        <Flex align="center" gap={6}>
          {key(dot, 10, 10)}
          This person
        </Flex>
        <Flex align="center" gap={6}>
          {key(middleHalf, 16, 8)}
          Middle half
        </Flex>
        <Flex align="center" gap={6}>
          {key(medianLine, 3, 12)}
          Median
        </Flex>
      </Flex>
    </div>
  );
}
