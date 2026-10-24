/**
 * A radio group's role and name. Ant Design passes them to the group's box but doesn't declare
 * them, and without the role the aria-required that Form.Item adds there means nothing.
 */
export const radioGroup = (label: string) => ({ role: "radiogroup", "aria-label": label });
