import type { Employee, EmployeeInput } from "../../api/employees";

/** The details form: everything but the salary, which has its own history on the record. */
export type DetailsValues = EmployeeInput;

/** A record as the edit form starts from it. */
export const formValues = (employee: Employee): DetailsValues => ({
  employee_code: employee.employee_code,
  full_name: employee.full_name,
  email: employee.email,
  country: employee.country.code,
  department: employee.department.id,
  job_title: employee.job_title,
  hire_date: employee.hire_date,
});
