import { describe, expect, it } from "vitest";

import { json, problem, stubApi } from "../test/api";
import { getJson, HttpError, sendJson } from "./http";

describe("http", () => {
  it("sends a write as JSON with the headers given", async () => {
    const api = stubApi({ "PATCH /api/v1/things/1/": () => json({ ok: true }) });

    expect(await sendJson("PATCH", "/api/v1/things/1/", { a: 1 }, { "If-Match": '"3"' })).toEqual({
      ok: true,
    });
    const init = api.mock.calls[0][1];
    expect(init?.body).toBe('{"a":1}');
    expect(init?.headers).toMatchObject({ "Content-Type": "application/json", "If-Match": '"3"' });
  });

  it("resolves a 204 to undefined", async () => {
    stubApi({ "DELETE /api/v1/things/1/": () => new Response(null, { status: 204 }) });

    expect(await sendJson("DELETE", "/api/v1/things/1/")).toBeUndefined();
  });

  it("turns an API error into an HttpError with the server's explanation", async () => {
    stubApi({ "GET /api/v1/things/": () => problem(422, "No exchange rate for XYZ.") });

    await expect(getJson("/api/v1/things/")).rejects.toMatchObject({
      status: 422,
      message: "No exchange rate for XYZ.",
    });
  });

  it("keeps the problem's extra fields, such as field errors and the clashing record", async () => {
    const body = { status: 409, detail: "Taken.", errors: { email: ["Taken."] }, existing_id: 7 };
    stubApi({ "POST /api/v1/things/": () => json(body, 409) });

    const error = await sendJson("POST", "/api/v1/things/").catch((caught: unknown) => caught);

    expect(error).toBeInstanceOf(HttpError);
    expect((error as HttpError).problem).toEqual(body);
  });

  it("falls back to the status when an error isn't JSON", async () => {
    stubApi({ "GET /api/v1/things/": () => new Response("<html>Bad gateway</html>", { status: 502 }) });

    await expect(getJson("/api/v1/things/")).rejects.toMatchObject({ status: 502 });
  });

  it("keeps the request id to quote, from the problem or else the response header", async () => {
    stubApi({
      "GET /api/v1/crash/": () =>
        json({ status: 500, detail: "Something went wrong on our side.", request_id: "a1b2c3d4" }, 500),
      "GET /api/v1/gateway/": () =>
        new Response("<html>Bad gateway</html>", {
          status: 502,
          headers: { "X-Request-ID": "e5f6a7b8" },
        }),
    });

    await expect(getJson("/api/v1/crash/")).rejects.toMatchObject({ requestId: "a1b2c3d4" });
    await expect(getJson("/api/v1/gateway/")).rejects.toMatchObject({ requestId: "e5f6a7b8" });
  });

  it("reports an unreachable server as status 0 with a plain message", async () => {
    stubApi({ "GET /api/v1/things/": () => Promise.reject(new TypeError("Failed to fetch")) });

    await expect(getJson("/api/v1/things/")).rejects.toEqual(
      new HttpError(0, "Can't reach the server. Check your connection and try again."),
    );
  });
});
