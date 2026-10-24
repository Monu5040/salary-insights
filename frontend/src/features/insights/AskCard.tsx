import { Alert, Button, Card, Input, Typography } from "antd";
import { useState } from "react";
import { useSearchParams } from "react-router";

import type { AskedQuery } from "../../api/insights";
import { HttpError } from "../../api/http";
import { ErrorAlert } from "../../components/ErrorAlert";
import { CardTitle } from "../../components/Titles";
import { GroupsTable } from "./Explorer";
import { useAsk } from "./queries";

const EXAMPLE = "Median salary by department in India, in rupees";

/** A question in plain English, answered by the explorer (design §4). Only the question
 *  leaves for Groq; the numbers come from our own database. */
export function AskCard() {
  const [question, setQuestion] = useState("");
  const asked = useAsk();
  const [params, setParams] = useSearchParams();
  const answer = asked.data;

  /** Put the question's reading into the explorer and the page's scope, to refine it there. */
  function openInExplorer(query: AskedQuery) {
    const next = new URLSearchParams(params);
    const lists: Record<string, (string | number)[]> = {
      metric: query.metric,
      by: query.by.length ? query.by : [""],
      country: query.country,
      department: query.department,
      currency: query.currency ? [query.currency] : [],
      as_of: query.as_of ? [query.as_of] : [],
    };
    for (const [key, values] of Object.entries(lists)) {
      next.delete(key);
      for (const value of values) next.append(key, String(value));
    }
    setParams(next);
    document.getElementById("explorer")?.scrollIntoView({ behavior: "smooth" });
  }

  return (
    <Card title={<CardTitle>Ask a question</CardTitle>} style={{ marginBottom: 16 }}>
      <Input.Search
        aria-label="Question"
        placeholder={EXAMPLE}
        enterButton="Ask"
        maxLength={300}
        value={question}
        loading={asked.isPending}
        onChange={(event) => setQuestion(event.target.value)}
        onSearch={(value) => {
          if (value.trim()) asked.mutate(value.trim());
        }}
      />
      {asked.error && (
        <div style={{ marginTop: 16 }}>
          {asked.error instanceof HttpError && asked.error.status === 429 ? (
            <Alert type="warning" showIcon message="Too many questions: wait a minute." />
          ) : (
            <ErrorAlert error={asked.error} />
          )}
        </div>
      )}
      {answer && !asked.isPending && !asked.error && (
        <div style={{ marginTop: 16 }}>
          <Typography.Paragraph>
            {answer.summary}{" "}
            <Typography.Text type="secondary">{answer.answer.fx_basis}.</Typography.Text>
          </Typography.Paragraph>
          <GroupsTable
            groups={answer.answer.groups}
            currency={answer.answer.currency}
            metrics={answer.answer.metrics}
            by={answer.answer.by}
          />
          <Button style={{ marginTop: 12 }} onClick={() => openInExplorer(answer.query)}>
            Open in the explorer
          </Button>
        </div>
      )}
    </Card>
  );
}
