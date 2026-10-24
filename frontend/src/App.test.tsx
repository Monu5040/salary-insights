import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { json, stubApi } from "./test/api";
import { renderApp } from "./test/renderApp";

const ready = () => json({ status: "ok" });

describe("App shell", () => {
  it("opens on Insights, with no sign-in, and lists the main sections", async () => {
    stubApi({ "GET /readyz/": ready });
    renderApp("/");

    expect(await screen.findByRole("heading", { name: "Insights" })).toBeInTheDocument();
    for (const name of ["Insights", "Employees", "Import"]) {
      expect(screen.getByRole("menuitem", { name })).toBeInTheDocument();
    }

  });

  it("moves between sections from the menu", async () => {
    stubApi({ "GET /readyz/": ready });
    renderApp("/insights");

    await userEvent.click(await screen.findByRole("menuitem", { name: "Employees" }));

    expect(await screen.findByRole("heading", { name: "Employees" })).toBeInTheDocument();
  });

  it("shows whether the API is ready", async () => {
    stubApi({ "GET /readyz/": ready });
    renderApp("/insights");

    expect(await screen.findByText("API: ready")).toBeInTheDocument();
  });

  it("shows the API as unavailable when the readiness check fails", async () => {
    stubApi({ "GET /readyz/": () => json({ status: "unavailable" }, 503) });
    renderApp("/insights");

    expect(await screen.findByText("API: unavailable")).toBeInTheDocument();
  });
});

describe("Pages that aren't there, or break", () => {
  it("says a page doesn't exist instead of sending you elsewhere", async () => {
    stubApi({ "GET /readyz/": ready });
    renderApp("/payroll-2019");

    expect(await screen.findByText("Page not found")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("link", { name: "Go to Insights" }));
    expect(await screen.findByRole("heading", { name: "Insights" })).toBeInTheDocument();
  });

  it("keeps the app usable when a page breaks", async () => {
    vi.spyOn(console, "error").mockImplementation(() => {}); // React reports the error too
    stubApi({
      "GET /readyz/": ready,
      "GET /api/v1/employees/7/": () => json({ id: 7 }), // a record the page can't draw
    });
    renderApp("/employees/7");

    expect(await screen.findByText("Something went wrong on this page")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("menuitem", { name: "Insights" }));
    expect(await screen.findByRole("heading", { name: "Insights" })).toBeInTheDocument();
  });
});

describe("Finding your way without a mouse", () => {
  it("names the browser tab after the page, which has one main heading", async () => {
    stubApi({ "GET /readyz/": ready });
    renderApp("/insights");

    expect(await screen.findByRole("heading", { level: 1, name: "Insights" })).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(document.title).toBe("Insights · Salary Insights");
  });

  it("lets keyboard users skip past the header to the page", async () => {
    stubApi({ "GET /readyz/": ready });
    renderApp("/insights");
    await screen.findByRole("heading", { level: 1, name: "Insights" });

    await userEvent.tab();
    expect(screen.getByRole("link", { name: "Skip to content" })).toHaveFocus();
    await userEvent.keyboard("{Enter}");
    expect(screen.getByRole("main")).toHaveFocus();
  });
});
