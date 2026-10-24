import { Alert, Button } from "antd";

import { HttpError } from "../../api/http";
import { ErrorAlert } from "../../components/ErrorAlert";

type Props = { error: Error | null; onReload: () => void };

/** Why a save failed. A 412 means someone else saved first, so offer to reload. */
export function SaveError({ error, onReload }: Props) {
  if (!error) return null;
  if (error instanceof HttpError && error.status === 412) {
    return (
      <Alert
        type="warning"
        showIcon
        style={{ marginBottom: 16 }}
        message="Someone else changed this employee while you were working."
        description="Reload to see their changes, then make yours again."
        action={<Button onClick={onReload}>Reload</Button>}
      />
    );
  }
  return <ErrorAlert error={error} />;
}
