import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  correctChange,
  type Employee,
  fetchSalaries,
  recordChange,
  removeChange,
  type SalaryChangeInput,
  type SalaryHistory,
} from "../../api/employees";
import { employeeKeys } from "../employees/queries";

// Under the employee's key, so reloading an employee reloads the history too.
export const salaryKeys = {
  history: (id: number) => ["employees", id, "salaries"] as const,
};

export const useSalaries = (id: number) =>
  useQuery({ queryKey: salaryKeys.history(id), queryFn: () => fetchSalaries(id) });

/** After a salary write: the server's history and the employee's new version, since a
 *  salary change is a change to their record. Then the record again (its salary is the one
 *  in force today), peers, the directory and the insights. */
function useSaved(employee: Employee) {
  const client = useQueryClient();
  return (history: SalaryHistory) => {
    client.setQueryData(salaryKeys.history(employee.id), history);
    client.setQueryData<Employee>(employeeKeys.one(employee.id), (current) =>
      current ? { ...current, version: history.employee_version } : current,
    );
    void client.invalidateQueries({ queryKey: employeeKeys.one(employee.id), exact: true });
    void client.invalidateQueries({ queryKey: employeeKeys.peers(employee.id) });
    void client.invalidateQueries({ queryKey: ["employees", "list"] });
    void client.invalidateQueries({ queryKey: ["insights"] });
  };
}

// Never optimistic: the screen changes once the server has saved (CLAUDE.md, Frontend).
export function useRecordChange(employee: Employee) {
  return useMutation({
    mutationFn: (input: SalaryChangeInput) => recordChange(employee.id, employee.version, input),
    onSuccess: useSaved(employee),
  });
}

export function useCorrectChange(employee: Employee) {
  return useMutation({
    mutationFn: ({ id, input }: { id: number; input: Partial<SalaryChangeInput> }) =>
      correctChange(employee.id, employee.version, id, input),
    onSuccess: useSaved(employee),
  });
}

export function useRemoveChange(employee: Employee) {
  return useMutation({
    mutationFn: (changeId: number) => removeChange(employee.id, employee.version, changeId),
    onSuccess: useSaved(employee),
  });
}
