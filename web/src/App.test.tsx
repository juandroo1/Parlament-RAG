import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { AskResponse } from "./api";
import App from "./App";
import { SPEECH } from "./test/fixtures";

const ANSWERED: AskResponse = {
  answer: "Rösti betonte den Winterstrom [1]. Die Motion wurde abgelehnt [2].",
  insufficient_context: false,
  insufficient_reason: null,
  sources: [
    SPEECH,
    {
      ...SPEECH,
      number: 2,
      source_key: "business:20253906",
      source_type: "business",
      speaker_name: null,
      speaker_function: null,
      council: null,
      business_numbers: ["25.3906"],
      section: "Stellungnahme des Bundesrates",
      text: "Der Bundesrat beantragt die Ablehnung der Motion.",
      url: "https://www.parlament.ch/geschaeft",
    },
  ],
  usage: {
    model: "claude-haiku-5-5",
    backend: "api",
    input_tokens: 9100,
    output_tokens: 1300,
    cost_usd: 0.0016,
    cost_estimated: false,
    latency_ms: 6040,
  },
};

function mockFetch(status: number, body: unknown) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: () => Promise.resolve(body),
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

async function askQuestion(question = "Was sagte Bundesrat Rösti zum Winterstrom?") {
  const user = userEvent.setup();
  render(<App />);
  await user.type(screen.getByLabelText(/Ihre Frage/), question);
  await user.click(screen.getByRole("button", { name: "Fragen" }));
  return user;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("zeigt Antwort, klickbare Zitate und Quellen mit Metadaten und Link", async () => {
    mockFetch(200, ANSWERED);
    const user = await askQuestion();

    expect(await screen.findByRole("heading", { name: "Antwort" })).toBeInTheDocument();
    const citation = screen.getByRole("link", { name: "Quelle 1" });
    expect(citation).toHaveAttribute("href", "#quelle-1");

    const sources = screen.getByRole("heading", { name: "Quellen" }).nextElementSibling as HTMLElement;
    const items = within(sources).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(within(items[0]).getByText("Rösti Albert (Bundesrat)")).toBeInTheDocument();
    expect(within(items[0]).getByText("Nationalrat · 30.09.2026 · 26.9022")).toBeInTheDocument();
    expect(within(items[0]).getByRole("link", { name: /Originalstelle auf parlament.ch/ })).toHaveAttribute(
      "href",
      "https://www.parlament.ch/votum47",
    );
    expect(within(items[1]).getByText("Geschäft 25.3906 · Stellungnahme des Bundesrates")).toBeInTheDocument();
    expect(screen.getByText(/claude-haiku-5-5/)).toBeInTheDocument();

    await user.click(citation);
    expect(document.getElementById("quelle-1")).toHaveFocus();
    expect(document.getElementById("quelle-1")?.className).toContain("border-red-700");
  });

  it("schickt die gewählten Filter mit", async () => {
    const fetchMock = mockFetch(200, ANSWERED);
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByLabelText(/Ihre Frage/), "Frage zur AHV?");
    await user.click(screen.getByRole("button", { name: /Filter/ }));
    await user.selectOptions(screen.getByLabelText("Rat"), "SR");
    await user.selectOptions(screen.getByLabelText(/Fraktion/), "RL");
    expect(screen.getByText(/nur Voten durchsucht, keine Geschäftstexte/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Fragen" }));

    await screen.findByRole("heading", { name: "Antwort" });
    expect(JSON.parse(fetchMock.mock.calls[0][1].body)).toEqual({
      question: "Frage zur AHV?",
      filters: { council: "SR", parl_group: "RL" },
    });
  });

  it("zeigt den Hinweis, wenn die Quellen nicht reichen", async () => {
    mockFetch(200, {
      ...ANSWERED,
      answer: "Zu dieser Frage habe ich keine ausreichende Grundlage gefunden.",
      insufficient_context: true,
      insufficient_reason: "low_similarity",
      sources: [],
      usage: { ...ANSWERED.usage, model: null, input_tokens: 0, output_tokens: 0, cost_usd: 0 },
    });
    await askQuestion("Wie entschied der Bieler Stadtrat?");

    expect(await screen.findByRole("heading", { name: "Keine ausreichende Grundlage" })).toBeInTheDocument();
    expect(screen.getByText(/passen zu wenig zur Frage/)).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Quellen" })).not.toBeInTheDocument();
  });

  it("zeigt Fehlermeldungen der API", async () => {
    mockFetch(503, { detail: "LLM nicht verfügbar: ANTHROPIC_API_KEY fehlt." });
    await askQuestion();
    expect(await screen.findByRole("alert")).toHaveTextContent("ANTHROPIC_API_KEY fehlt");
  });

  it("deaktiviert den Knopf bei zu kurzer Frage und während der Suche", async () => {
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise(() => {})));
    const user = userEvent.setup();
    render(<App />);
    const button = screen.getByRole("button", { name: "Fragen" });
    expect(button).toBeDisabled();
    await user.type(screen.getByLabelText(/Ihre Frage/), "Frage?");
    await user.click(button);
    expect(screen.getByRole("status")).toHaveTextContent("5 bis 15 Sekunden");
    expect(screen.getByRole("button", { name: "Suche läuft …" })).toBeDisabled();
  });

  it("nennt Datenquelle und Lizenz", () => {
    render(<App />);
    // Nutzungsbedingungen der Parlamentsdienste: Quelle, Datum des Downloads, nicht amtlich.
    expect(screen.getByText(/Parlamentsdienste der Bundesversammlung, Bern/)).toBeInTheDocument();
    expect(screen.getByText(/heruntergeladen am 12\.\s+und 13\. November 2026/)).toBeInTheDocument();
    expect(screen.getByText(/Keine amtliche Veröffentlichung/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "MIT-Lizenz" })).toBeInTheDocument();
    expect(screen.getByText(/bewertet keine Personen, Parteien oder Vorlagen/)).toBeInTheDocument();
  });
});
