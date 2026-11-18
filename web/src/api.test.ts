import { describe, expect, it, vi } from "vitest";
import { ask, buildRequest } from "./api";

function respond(
  status: number,
  body: unknown,
  headers: Record<string, string> = {},
) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    headers: new Headers(headers),
    json: () => Promise.resolve(body),
  });
}

describe("buildRequest", () => {
  it("lässt leere Filter weg", () => {
    expect(buildRequest("  Frage?  ", { council: "", parl_group: "" })).toEqual(
      { question: "Frage?" },
    );
  });

  it("übernimmt gesetzte Filter", () => {
    expect(
      buildRequest("Frage?", {
        council: "SR",
        date_from: "2025-01-01",
        date_to: "",
        parl_group: "RL",
      }),
    ).toEqual({
      question: "Frage?",
      filters: { council: "SR", date_from: "2025-01-01", parl_group: "RL" },
    });
  });
});

describe("ask", () => {
  it("schickt die Anfrage an /api/ask", async () => {
    const fetchMock = respond(200, { answer: "Antwort [1].", sources: [] });
    const result = await ask({ question: "Frage?" }, fetchMock);

    expect(result.answer).toBe("Antwort [1].");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/ask");
    expect(init.method).toBe("POST");
    expect(JSON.parse(init.body)).toEqual({ question: "Frage?" });
  });

  it("übernimmt die Meldung der API bei Fehlern", async () => {
    const fetchMock = respond(503, {
      detail: "LLM nicht verfügbar: ANTHROPIC_API_KEY fehlt.",
    });
    await expect(ask({ question: "Frage?" }, fetchMock)).rejects.toMatchObject({
      message: "LLM nicht verfügbar: ANTHROPIC_API_KEY fehlt.",
      status: 503,
      kind: "http",
      detail: "LLM nicht verfügbar: ANTHROPIC_API_KEY fehlt.",
    });
  });

  it("fasst Validierungsfehler zusammen", async () => {
    const fetchMock = respond(422, {
      detail: [{ msg: "String should have at least 3 characters" }],
    });
    await expect(ask({ question: "ab" }, fetchMock)).rejects.toMatchObject({
      message:
        "Die Eingabe ist ungültig: String should have at least 3 characters",
      kind: "validation",
      detail: "String should have at least 3 characters",
    });
  });

  it("meldet eine nicht erreichbare API", async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValue(new TypeError("Failed to fetch"));
    await expect(ask({ question: "Frage?" }, fetchMock)).rejects.toMatchObject({
      kind: "network",
      status: null,
    });
  });

  it("liest Fehlercode und Wartezeit aus den Headern (Task 7.5)", async () => {
    const fetchMock = respond(
      429,
      { detail: "Zu viele Fragen: Die Demo erlaubt 10 Fragen pro Stunde." },
      { "X-Error-Code": "rate_limit", "Retry-After": "720" },
    );
    await expect(ask({ question: "Frage?" }, fetchMock)).rejects.toMatchObject({
      status: 429,
      code: "rate_limit",
      retryAfter: 720,
      detail: "Zu viele Fragen: Die Demo erlaubt 10 Fragen pro Stunde.",
    });
  });

  it("kommt ohne Header aus", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: false,
      status: 503,
      json: () => Promise.resolve({ detail: "kaputt" }),
    });
    await expect(ask({ question: "Frage?" }, fetchMock)).rejects.toMatchObject({
      code: null,
      retryAfter: null,
    });
  });
});
