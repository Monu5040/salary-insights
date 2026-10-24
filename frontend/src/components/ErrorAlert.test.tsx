import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { HttpError } from "../api/http";
import { ErrorAlert } from "./ErrorAlert";

describe("ErrorAlert", () => {
  it("gives a server fault's reference to quote, and a way to try again", async () => {
    const retry = vi.fn();
    const error = new HttpError(500, "Something went wrong on our side.", undefined, "a1b2c3d4");
    render(<ErrorAlert error={error} onRetry={retry} />);

    expect(screen.getByRole("alert")).toHaveTextContent("Something went wrong on our side.");
    expect(screen.getByText("a1b2c3d4")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(retry).toHaveBeenCalledOnce();
  });

  it("gives no reference when the request itself was the problem", () => {
    const error = new HttpError(422, "No exchange rate for KWD on 1 Jan 2020.", undefined, "a1b2c3d4");
    render(<ErrorAlert error={error} />);

    expect(screen.getByRole("alert")).toHaveTextContent("No exchange rate for KWD on 1 Jan 2020.");
    expect(screen.queryByText("a1b2c3d4")).not.toBeInTheDocument();
  });
});
