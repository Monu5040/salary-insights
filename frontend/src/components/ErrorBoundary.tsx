import { Button, Result } from "antd";
import { Component, type ErrorInfo, type ReactNode } from "react";
import { Link } from "react-router";

import { PageTitle } from "./Titles";

type Props = { children: ReactNode };
type State = { failed: boolean };

/**
 * A page that throws while drawing shows what to do instead of a blank screen, and the rest
 * of the app keeps working. The shell keys it on the address, so moving on starts afresh.
 */
export class ErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    // Until error tracking arrives at go-live (M12), the browser console is the record.
    console.error(error, info.componentStack);
  }

  render() {
    if (!this.state.failed) return this.props.children;
    return (
      <Result
        status="error"
        title={<PageTitle style={{ margin: 0 }}>Something went wrong on this page</PageTitle>}
        subTitle="Reload to try again. If it keeps happening, tell IT what you were doing."
        extra={[
          <Button key="reload" type="primary" onClick={() => window.location.reload()}>
            Reload
          </Button>,
          <Link key="home" to="/insights">
            Go to Insights
          </Link>,
        ]}
      />
    );
  }
}
