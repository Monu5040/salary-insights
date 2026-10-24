import { Col, Row } from "antd";

import { ErrorAlert } from "../../components/ErrorAlert";
import { PageHeader } from "../../components/PageHeader";
import { useConfig } from "../reference/hooks";
import { Explorer } from "./Explorer";
import { Headline } from "./Headline";
import { PresetCard } from "./PresetCard";
import { usePresets, useSummary } from "./queries";
import { ScopeBar } from "./ScopeBar";
import { useScope } from "./scope";

/** Answers to pay questions by country, department and job title, in any currency
 *  (design §4, §8). */
export function InsightsPage() {
  const { params, scope, update } = useScope();
  const summary = useSummary(scope);
  const presets = usePresets();
  const config = useConfig().data;
  const currency =
    params.get("currency") ?? summary.data?.currency ?? config?.reporting_currency ?? "USD";

  return (
    <>
      <PageHeader
        title="Insights"
        subtitle="Headcount, payroll and salaries by country, department and job title"
      />
      <ScopeBar params={params} onChange={update} currency={currency} />
      {summary.error && <ErrorAlert error={summary.error} onRetry={() => void summary.refetch()} />}
      {summary.data && <Headline summary={summary.data} />}
      <Row gutter={[16, 16]}>
        {presets.data?.map((preset) => (
          <Col key={preset.id} xs={24} xl={preset.chart === "table" ? 24 : 12}>
            <PresetCard preset={preset} scope={scope} />
          </Col>
        ))}
        <Col xs={24}>
          <Explorer scope={scope} />
        </Col>
      </Row>
    </>
  );
}
