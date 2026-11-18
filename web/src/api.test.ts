import { describe, expect, it, vi } from "vitest";
import { ask, buildRequest } from "./api";

function respond(status: number, body: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
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
});
