import { BarChartOutlined, TeamOutlined } from "@ant-design/icons";
import { Flex, Layout, Menu } from "antd";
import { Navigate, Outlet, Route, Routes, useLocation, useNavigate } from "react-router";

import { ApiStatus } from "./components/ApiStatus";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Logo } from "./components/Logo";
import { NotFound } from "./components/NotFound";

// Icons are decoration beside their words, so screen readers skip them.
const SECTIONS = [
  { key: "/insights", label: "Insights", icon: <BarChartOutlined aria-hidden /> },
  { key: "/employees", label: "Employees", icon: <TeamOutlined aria-hidden /> },
];

export function App() {
  return (
    <Routes>
      <Route element={<Shell />}>
        <Route index element={<Navigate to="/insights" replace />} />
        <Route path="*" element={<NotFound />} />
      </Route>
    </Routes>
  );
}

function Shell() {
  const location = useLocation();
  const navigate = useNavigate();
  const selected = SECTIONS.find((section) => location.pathname.startsWith(section.key));

  return (
    <Layout hasSider style={{ minHeight: "100vh" }}>
      <a
        className="skip-link"
        href="#content"
        onClick={(event) => {
          // Move focus without changing the address.
          event.preventDefault();
          document.getElementById("content")?.focus();
        }}
      >
        Skip to content
      </a>
      {/* Stays in view while a long page scrolls past it. */}
      <Layout.Sider
        width={240}
        className="sider"
        style={{ position: "sticky", top: 0, height: "100vh", overflow: "auto" }}
      >
        <Flex vertical style={{ height: "100%" }}>
          {/* The product's name, not a heading: each page has its own (components/Titles). */}
          <Flex align="center" gap={12} style={{ padding: "22px 20px 26px" }}>
            <Logo size={34} />
            <div style={{ lineHeight: 1.25 }}>
              <div className="sider-product">Salary Insights</div>
              <div className="sider-dim">ACME HR</div>
            </div>
          </Flex>
          <nav aria-label="Sections" style={{ flex: 1 }}>
            <Menu
              theme="dark"
              mode="inline"
              items={SECTIONS}
              selectedKeys={selected ? [selected.key] : []}
              onClick={({ key }) => void navigate(key)}
            />
          </nav>
          <Flex vertical gap={14} className="sider-footer">
            <ApiStatus />
          </Flex>
        </Flex>
      </Layout.Sider>
      <Layout.Content
        id="content"
        tabIndex={-1}
        style={{ padding: "28px 32px 48px", outline: "none", minWidth: 0 }}
      >
        <div style={{ maxWidth: 1400, margin: "0 auto" }}>
          <ErrorBoundary key={location.pathname}>
            <Outlet />
          </ErrorBoundary>
        </div>
      </Layout.Content>
    </Layout>
  );
}
