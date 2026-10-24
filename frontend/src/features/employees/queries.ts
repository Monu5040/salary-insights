import { keepPreviousData, useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  createEmployee,
  deleteEmployee,
  type Employee,
  type EmployeeInput,
  fetchEmployee,
  fetchPeers,
  listEmployees,
  updateEmployee,
} from "../../api/employees";

export const employeeKeys = {
  list: (query: string) => ["employees", "list", query] as const,
  one: (id: number) => ["employees", id] as const,
  // Under the employee's key, so reloading an employee reloads these too.
  peers: (id: number) => ["employees", id, "peers"] as const,
};

/** A directory page; the previous page stays on screen while the next one loads. */
export const useDirectory = (query: string) =>
  useQuery({
    queryKey: employeeKeys.list(query),
    queryFn: () => listEmployees(query),
    placeholderData: keepPreviousData,
  });

export const employeeQuery = (id: number) => ({
  queryKey: employeeKeys.one(id),
  queryFn: () => fetchEmployee(id),
});

export const useEmployee = (id: number) => useQuery(employeeQuery(id));

export const usePeers = (id: number) =>
  useQuery({ queryKey: employeeKeys.peers(id), queryFn: () => fetchPeers(id) });

/** After a change: show the server's record, then refresh peers, directory pages and the
 *  insights. Never optimistic: the screen changes only once the server has saved. */
function useSaved() {
  const client = useQueryClient();
  return (employee: Employee) => {
    client.setQueryData(employeeKeys.one(employee.id), employee);
    void client.invalidateQueries({ queryKey: ["employees", "list"] });
    void client.invalidateQueries({ queryKey: employeeKeys.peers(employee.id) });
    void client.invalidateQueries({ queryKey: ["insights"] });
  };
}

export function useCreateEmployee() {
  return useMutation({ mutationFn: createEmployee, onSuccess: useSaved() });
}

// Each write sends the version on screen, so a newer one on the server is a 412.
export function useUpdateEmployee(employee: Employee) {
  return useMutation({
    mutationFn: (input: Partial<EmployeeInput>) =>
      updateEmployee(employee.id, employee.version, input),
    onSuccess: useSaved(),
  });
}

export function useDeleteEmployee(employee: Employee) {
  const client = useQueryClient();
  return useMutation({
    mutationFn: () => deleteEmployee(employee.id, employee.version),
    onSuccess: () => {
      client.removeQueries({ queryKey: employeeKeys.one(employee.id) });
      void client.invalidateQueries({ queryKey: ["employees", "list"] });
      void client.invalidateQueries({ queryKey: ["insights"] });
    },
  });
}

/** Reload everything about one employee (record and peers), after a 412 says someone else
 *  changed them. */
export function useReloadEmployee(id: number) {
  const client = useQueryClient();
  return () => client.invalidateQueries({ queryKey: employeeKeys.one(id) });
}
