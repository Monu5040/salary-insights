import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

/** Pick an option in an Ant Design select, by the field's label and the option's text. */
export async function choose(label: string, option: string) {
  await userEvent.click(await screen.findByRole("combobox", { name: label }));
  const item = await waitFor(() => {
    // The newest dropdown: closed ones stay in the page.
    const options = document.querySelectorAll(`.ant-select-item-option[title="${option}"]`);
    const found = [...options].at(-1);
    if (!found) throw new Error(`no option ${option}`);
    return found as HTMLElement;
  });
  await userEvent.click(item);
}
