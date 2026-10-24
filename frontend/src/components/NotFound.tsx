import { Result } from "antd";
import { Link } from "react-router";

import { PageTitle } from "./Titles";

/** An address the app has no page for, such as an old bookmark or a mistyped link. */
export function NotFound() {
  return (
    <Result
      status="404"
      title={<PageTitle style={{ margin: 0 }}>Page not found</PageTitle>}
      subTitle="This address isn't a page in the app. The link may be old or mistyped."
      extra={<Link to="/insights">Go to Insights</Link>}
    />
  );
}
