import {
  Breadcrumb,
  Button,
  Card,
  Col,
  Divider,
  Flex,
  Popconfirm,
  Result,
  Row,
  Space,
  Spin,
  Typography,
} from "antd";
import { useState } from "react";
import { Link, useNavigate, useParams } from "react-router";

import type { Employee } from "../../api/employees";
import { HttpError } from "../../api/http";
import { ErrorAlert } from "../../components/ErrorAlert";
import { Facts } from "../../components/Facts";
import { PersonAvatar } from "../../components/PersonAvatar";
import { PageTitle } from "../../components/Titles";
import { formatDate } from "../../lib/format";
import { PeersCard } from "../salaries/PeersCard";
import { SalaryCard } from "../salaries/SalaryCard";
import { EditEmployeeDrawer } from "./EditEmployeeDrawer";
import { useDeleteEmployee, useEmployee, useReloadEmployee } from "./queries";
import { SaveError } from "./SaveError";

export function EmployeePage() {
  const id = Number(useParams().id);
  const employee = useEmployee(id);

  if (employee.isPending) return <Spin />;
  if (employee.isError) {
    if (employee.error instanceof HttpError && employee.error.status === 404) {
      return (
        <Result
          status="404"
          title={<PageTitle style={{ margin: 0 }}>No such employee</PageTitle>}
          extra={<Link to="/employees">Back to employees</Link>}
        />
      );
    }
    return <ErrorAlert error={employee.error} onRetry={() => void employee.refetch()} />;
  }
  return <Profile employee={employee.data} />;
}

function Profile({ employee }: { employee: Employee }) {
  const [editing, setEditing] = useState(false);
  const remove = useDeleteEmployee(employee);
  const reload = useReloadEmployee(employee.id);
  const navigate = useNavigate();

  return (
    <>
      <Breadcrumb
        items={[{ title: <Link to="/employees">Employees</Link> }, { title: employee.full_name }]}
        style={{ marginBottom: 16 }}
      />
      <SaveError
        error={remove.error}
        onReload={() => {
          remove.reset();
          void reload();
        }}
      />
      <Card style={{ marginBottom: 16 }}>
        <Flex justify="space-between" align="flex-start" wrap gap={16}>
          <Flex align="center" gap={16} style={{ minWidth: 0 }}>
            <PersonAvatar name={employee.full_name} size={64} />
            <div style={{ minWidth: 0 }}>
              <PageTitle style={{ margin: 0 }}>{employee.full_name}</PageTitle>
              {/* Each in its own element, so each can be found and read on its own. */}
              <Typography.Text type="secondary">
                <span>{employee.job_title}</span> · <span>{employee.department.name}</span> ·{" "}
                <span>{employee.country.name}</span>
              </Typography.Text>
            </div>
          </Flex>
          <Space>
            <Button onClick={() => setEditing(true)}>Edit details</Button>
            <Popconfirm
              title={`Delete ${employee.full_name}?`}
              description="Their record and salary history are removed for good."
              okText="Delete"
              okButtonProps={{ danger: true }}
              onConfirm={() =>
                remove.mutate(undefined, { onSuccess: () => void navigate("/employees") })
              }
            >
              <Button danger loading={remove.isPending}>
                Delete
              </Button>
            </Popconfirm>
          </Space>
        </Flex>
        <Divider style={{ margin: "20px 0" }} />
        <Facts
          items={[
            { label: "Employee code", value: employee.employee_code },
            { label: "Email", value: employee.email },
            { label: "Hire date", value: formatDate(employee.hire_date) },
          ]}
        />
      </Card>
      <Row gutter={16}>
        <Col xs={24} xl={14}>
          <SalaryCard employee={employee} />
        </Col>
        <Col xs={24} xl={10}>
          <PeersCard employee={employee} />
        </Col>
      </Row>
      <EditEmployeeDrawer employee={employee} open={editing} onClose={() => setEditing(false)} />
    </>
  );
}
