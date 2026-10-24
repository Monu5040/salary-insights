import { useMutation, useQueryClient } from "@tanstack/react-query";

import { applyImport, type DateFormat, previewImport } from "../../api/imports";

type Upload = { file: File; dateFormat: DateFormat };

/** A preview changes nothing, but it reads a whole file: a mutation, run when asked. */
export const usePreview = () =>
  useMutation({ mutationFn: ({ file, dateFormat }: Upload) => previewImport(file, dateFormat) });

/** Apply the previewed file; afterwards every employee and insight may have changed. */
export function useApply() {
  const client = useQueryClient();
  return useMutation({
    mutationFn: ({ file, dateFormat, fingerprint }: Upload & { fingerprint: string }) =>
      applyImport(file, dateFormat, fingerprint),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: ["employees"] });
      void client.invalidateQueries({ queryKey: ["insights"] });
    },
  });
}
