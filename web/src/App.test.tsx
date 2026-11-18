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

async function askQuestion(
  question = "Was sagte Bundesrat Rösti zum Winterstrom?",
) {
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

    expect(
      await screen.findByRole("heading", { name: "Antwort" }),
    ).toBeInTheDocument();
    const citation = screen.getByRole("link", { name: "Quelle 1" });
    expect(citation).toHaveAttribute("href", "#quelle-1");

    const sources = screen.getByRole("heading", { name: "Quellen" })
      .nextElementSibling as HTMLElement;
    const items = within(sources).getAllByRole("listitem");
    expect(items).toHaveLength(2);
    expect(
      within(items[0]).getByText("Rösti Albert (Bundesrat)"),
    ).toBeInTheDocument();
    expect(
      within(items[0]).getByText("Nationalrat · 30.09.2026 · 26.9022"),
    ).toBeInTheDocument();
    expect(
      within(items[0]).getByRole("link", {
        name: /Originalstelle auf parlament.ch/,
      }),
    ).toHaveAttribute("href", "https://www.parlament.ch/votum47");
    expect(
      within(items[1]).getByText(
        "Geschäft 25.3906 · Stellungnahme des Bundesrates",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/claude-haiku-5-5/)).toBeInTheDocument();
    expect(screen.getByText("KI-Antwort aus 2 Quellen")).toBeInTheDocument();

    await user.click(citation);
    expect(document.getElementById("quelle-1")).toHaveFocus();
    expect(document.getElementById("quelle-1")?.className).toContain(
      "border-accent",
    );
  });

  it("schickt die gewählten Filter mit", async () => {
    const fetchMock = mockFetch(200, ANSWERED);
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByLabelText(/Ihre Frage/), "Frage zur AHV?");
    await user.click(screen.getByRole("button", { name: /Filter/ }));
    await user.selectOptions(screen.getByLabelText("Rat"), "SR");
    await user.selectOptions(screen.getByLabelText(/Fraktion/), "RL");
    expect(
      screen.getByText(/nur Voten durchsucht, keine Geschäftstexte/),
    ).toBeInTheDocument();
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
      usage: {
        ...ANSWERED.usage,
        model: null,
        input_tokens: 0,
        output_tokens: 0,
        cost_usd: 0,
      },
    });
    await askQuestion("Wie entschied der Bieler Stadtrat?");

    expect(
      await screen.findByRole("heading", {
        name: "Keine ausreichende Grundlage",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(/passen zu wenig zur Frage/)).toBeInTheDocument();
    expect(
      screen.queryByRole("heading", { name: "Quellen" }),
    ).not.toBeInTheDocument();
  });

  it("zeigt Fehlermeldungen der API", async () => {
    mockFetch(503, { detail: "LLM nicht verfügbar: ANTHROPIC_API_KEY fehlt." });
    await askQuestion();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "ANTHROPIC_API_KEY fehlt",
    );
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
    expect(
      screen.getByRole("button", { name: "Suche läuft …" }),
    ).toBeDisabled();
  });

  it("zeigt Logo und den Hinweis «Privates Projekt» in der Kopfzeile vor dem Formular", () => {
    render(<App />);
    const banner = screen.getByRole("banner");
    // Helles und dunkles Logo; sichtbar ist je nach Modus eines (CSS).
    const logos = within(banner).getAllByRole("img", {
      name: "Frag das Parlament",
    });
    expect(logos.map((logo) => logo.getAttribute("src"))).toEqual([
      expect.stringContaining("logo-light"),
      expect.stringContaining("logo-dark"),
    ]);
    expect(logos[0].closest("a")).toHaveAttribute("href", "#top");
    const notice = within(banner).getByText(
      /Privates Projekt – keine amtliche Veröffentlichung/,
    );
    const form = screen
      .getByRole("button", { name: "Fragen" })
      .closest("form")!;
    expect(
      notice.compareDocumentPosition(form) & Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", {
        level: 1,
        name: "Was wurde im Parlament gesagt?",
      }),
    ).toBeInTheDocument();
  });

  it("nennt Datenquelle und Lizenz", () => {
    render(<App />);
    // Nutzungsbedingungen der Parlamentsdienste: Quelle, Datum des Downloads, nicht amtlich.
    expect(
      screen.getByText(/Parlamentsdienste der Bundesversammlung, Bern/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/heruntergeladen am 12\.\s+und 13\. November 2026/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Keine amtliche Veröffentlichung/),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "MIT-Lizenz" }),
    ).toBeInTheDocument();
    expect(
      within(screen.getByRole("contentinfo")).getByText(
        /bewertet keine Personen, Parteien oder Vorlagen/,
      ),
    ).toBeInTheDocument();
  });

  it("wechselt die ganze Oberfläche auf Französisch (AK-10.1)", async () => {
    mockFetch(200, ANSWERED);
    const user = await askQuestion();
    await screen.findByRole("heading", { name: "Antwort" });

    await user.click(
      within(screen.getByRole("group", { name: "Sprache" })).getByRole(
        "button",
        { name: "Français" },
      ),
    );

    expect(document.documentElement.lang).toBe("fr");
    expect(window.localStorage.getItem("fdp-lang")).toBe("fr");
    expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent(
      "Qu’a-t-on dit au Parlement",
    );
    expect(
      screen.getByText(/Projet privé – pas une publication officielle/),
    ).toBeInTheDocument();
    expect(screen.getByLabelText(/Votre question/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Demander" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Réponse" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Réponse IA tirée de 2 sources"),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Source 1" })).toBeInTheDocument();
    expect(
      screen.getByText("Rösti Albert (Conseil fédéral)"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Conseil national · 30.09.2026 · 26.9022"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Objet 25.3906 · Stellungnahme des Bundesrates"),
    ).toBeInTheDocument();
    expect(
      screen.getAllByRole("link", {
        name: /Passage original sur parlament.ch/,
      }),
    ).toHaveLength(2);
    expect(
      screen.getByText(/Services du Parlement de l’Assemblée fédérale, Berne/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/téléchargées les 12 et 13 novembre 2026/),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: "licence MIT" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("group", { name: "Affichage" }),
    ).toBeInTheDocument();
    // Die Antwort selbst bleibt in der Sprache der Frage (AK-10.4).
    expect(
      screen.getByText(/Rösti betonte den Winterstrom/),
    ).toBeInTheDocument();
    // Ohne deutsche Reste in der Oberfläche (ausser Antwort und Daten der Quellen).
    for (const word of [
      "Fragen",
      "Quellen",
      "Beispiele:",
      "Filter",
      "Originalstelle",
    ]) {
      expect(
        screen.queryByRole("button", { name: word }),
      ).not.toBeInTheDocument();
    }
  });

  it("startet auf Französisch, wenn der Browser Französisch bevorzugt (AK-10.2)", () => {
    vi.spyOn(navigator, "languages", "get").mockReturnValue(["fr-CH", "de-CH"]);
    render(<App />);
    expect(document.documentElement.lang).toBe("fr");
    expect(document.title).toBe("Frag das Parlament");
    expect(screen.getByRole("button", { name: "Français" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
    expect(screen.getByText(/^Exemples/)).toBeInTheDocument();
    vi.restoreAllMocks();
  });

  it("zeigt Fehler der App in der gewählten Sprache", async () => {
    vi.spyOn(navigator, "languages", "get").mockReturnValue(["fr"]);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
    );
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByLabelText(/Votre question/), "Question ?");
    await user.click(screen.getByRole("button", { name: "Demander" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "L’API n’est pas joignable",
    );
    vi.restoreAllMocks();
  });

  it("zeigt das Rate-Limit der API auf Französisch mit Wartezeit (AK-10.3)", async () => {
    vi.spyOn(navigator, "languages", "get").mockReturnValue(["fr-CH"]);
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 429,
        headers: new Headers({
          "X-Error-Code": "rate_limit",
          "Retry-After": "1500",
        }),
        json: () =>
          Promise.resolve({
            detail: "Zu viele Fragen: Die Demo erlaubt 10 Fragen pro Stunde.",
          }),
      }),
    );
    const user = userEvent.setup();
    render(<App />);
    await user.type(screen.getByLabelText(/Votre question/), "Question ?");
    await user.click(screen.getByRole("button", { name: "Demander" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "Trop de questions en peu de temps. Veuillez réessayer dans 25 minutes.",
    );

    // Beim Sprachwechsel wechselt die Meldung mit.
    await user.click(screen.getByRole("button", { name: "Deutsch" }));
    expect(screen.getByRole("alert")).toHaveTextContent(
      "Bitte in 25 Minuten wieder versuchen.",
    );
    vi.restoreAllMocks();
  });
});
