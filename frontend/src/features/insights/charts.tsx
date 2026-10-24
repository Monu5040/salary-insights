import { Tag, theme, Typography } from "antd";

// Plain bars and ranges: the questions here are comparisons of a few groups, which
// these show clearly without a charting library. Each group is a list item whose name and
// value are text, so a screen reader reads the numbers; the bars themselves are hidden from it.

// The rows share one set of columns (subgrid), so every bar's track is the same width and
// lengths compare across rows, however long each row's words are.
const list = {
  display: "grid",
  gridTemplateColumns: "fit-content(32%) minmax(80px, 1fr) fit-content(45%)",
  columnGap: 16,
  rowGap: 10,
  alignItems: "center",
} as const;

const row = {
  display: "grid",
  gridColumn: "1 / -1",
  gridTemplateColumns: "subgrid",
  alignItems: "center",
} as const;

export type Bar = { key: string; label: string; value: number; text: string; note?: string };

/** One horizontal bar per group, scaled to the largest. */
export function Bars({ bars }: { bars: Bar[] }) {
  const { token } = theme.useToken();
  const largest = Math.max(0, ...bars.map((bar) => bar.value)) || 1;
  const track = { background: token.colorFillTertiary, height: 8, borderRadius: 8 };
  const fill = `linear-gradient(90deg, ${token.colorPrimaryBorderHover}, ${token.colorPrimary})`;
  return (
    <div role="list" style={list}>
      {bars.map((bar) => (
        <div key={bar.key} role="listitem" style={row}>
          <Typography.Text ellipsis={{ tooltip: bar.label }}>{bar.label}</Typography.Text>
          <div aria-hidden style={track}>
            <div
              style={{
                width: `${(Math.max(bar.value, 0) / largest) * 100}%`,
                minWidth: bar.value > 0 ? 4 : 0,
                height: "100%",
                borderRadius: 8,
                background: fill,
              }}
            />
          </div>
          <span style={{ fontWeight: 500, fontVariantNumeric: "tabular-nums" }}>
            {bar.text}
            {bar.note && (
              <Typography.Text type="secondary" style={{ fontSize: 12, fontWeight: 400 }}>
                {" "}
                {bar.note}
              </Typography.Text>
            )}
          </span>
        </div>
      ))}
    </div>
  );
}

export type Spread = {
  key: string;
  label: string;
  p10: number;
  p25: number;
  median: number;
  p75: number;
  p90: number;
  text: string;
  lowSample: boolean;
};

/** P10 to P90 per group on one scale: the middle half darker, the median as a line. */
export function RangeBars({ ranges }: { ranges: Spread[] }) {
  const low = Math.min(...ranges.map((range) => range.p10));
  const span = Math.max(...ranges.map((range) => range.p90)) - low || 1;
  const at = (value: number) => `${((value - low) / span) * 100}%`;
  const between = (from: number, to: number) => ({
    left: at(from),
    width: `${((to - from) / span) * 100}%`,
  });
  const piece = (top: number, height: number, background: string) =>
    ({ position: "absolute", top, height, background, borderRadius: height }) as const;
  const { token } = theme.useToken();
  const [whisker, middleHalf, medianLine] = [
    token.colorBorder,
    token.colorPrimaryBorder,
    token.colorPrimaryActive,
  ];

  return (
    <div role="list" style={list}>
      {ranges.map((range) => (
        <div key={range.key} role="listitem" style={row}>
          <Typography.Text ellipsis={{ tooltip: range.label }}>{range.label}</Typography.Text>
          <div aria-hidden style={{ position: "relative", height: 18 }}>
            <div style={{ ...piece(8, 2, whisker), ...between(range.p10, range.p90) }} />
            <div style={{ ...piece(4, 10, middleHalf), ...between(range.p25, range.p75) }} />
            <div style={{ ...piece(1, 16, medianLine), left: at(range.median), width: 3 }} />
          </div>
          <span style={{ fontVariantNumeric: "tabular-nums" }}>
            {range.text}
            {range.lowSample && (
              <Tag bordered={false} style={{ marginLeft: 6, marginRight: 0 }}>
                Under 5 people
              </Tag>
            )}
          </span>
        </div>
      ))}
    </div>
  );
}
