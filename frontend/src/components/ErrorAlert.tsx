import { Alert, Button, Typography } from "antd";

import { HttpError } from "../api/http";
import { errorReference } from "../lib/errors";

type Props = { error: Error; onRetry?: () => void };

/**
 * Why something failed, in the server's words. A request the server refused (4xx) is a
 * warning about the request; a fault on its side is an error, with the reference to quote.
 */
export function ErrorAlert({ error, onRetry }: Props) {
  const reference = errorReference(error);
  const refused = error instanceof HttpError && error.status >= 400 && error.status < 500;
  return (
    <Alert
      type={refused ? "warning" : "error"}
      showIcon
      style={{ marginBottom: 16 }}
      message={error.message}
      description={
        reference && (
          <>
            If it keeps happening, tell IT this reference:{" "}
            <Typography.Text code copyable>
              {reference}
            </Typography.Text>
          </>
        )
      }
      action={
        onRetry && (
          <Button size="small" onClick={onRetry}>
            Try again
          </Button>
        )
      }
    />
  );
}
