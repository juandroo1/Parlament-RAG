// Person und Zeitraum in der Oberfläche (Spec 003, AK-16.4, AK-17.3, AK-17.5, AK-18.1).
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { AskResponse } from "./api";
import App from "./App";
import {
  AMBIGUOUS,
  DETECTED_ANSWER,
  OUT_OF_RANGE,
  PARTIAL_RETRIED,
  apiMock,
} from "./test/fixtures";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

async function ask(question: string, ...answers: AskResponse[]) {
  const fetchMock = apiMock(...answers);
  vi.stubGlobal("fetch", fetchMock);
  const user = userEvent.setup();
  render(<App />);
  await user.type(screen.getByLabelText(/Ihre Frage/), question);
  await user.click(screen.getByRole("button", { name: "Fragen" }));
  return { user, fetchMock };
}

function askBodies(fetchMock: ReturnType<typeof apiMock>) {
  return fetchMock.mock.calls
    .filter(([url]) => url === "/api/ask")
    .map(([, init]) =>
      JSON.parse((init as unknown as RequestInit).body as string),
    );
}

describe("erkannte Filter", () => {
  it("zeigt Person und Zeitraum über der Antwort", async () => {
    await ask("Was sagte Bundesrat Rösti 2025?", DETECTED_ANSWER);
    expect(await screen.findByText("Gesucht in:")).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Filter «Voten von Rösti Albert» entfernen und neu suchen",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: "Filter «2025» entfernen und neu suchen",
      }),
    ).toBeInTheDocument();
  });

  it("fragt nach dem Entfernen ohne Erkennung, mit den übrigen Filtern", async () => {
    const { user, fetchMock } = await ask(
      "Was sagte Bundesrat Rösti 2025?",
      DETECTED_ANSWER,
      { ...DETECTED_ANSWER, filters: undefined },
    );
    await user.click(
      await screen.findByRole("button", { name: /Filter «2025» entfernen/ }),
    );
    expect(askBodies(fetchMock)).toEqual([
      { question: "Was sagte Bundesrat Rösti 2025?" },
      {
        question: "Was sagte Bundesrat Rösti 2025?",
        filters: { speaker: "Rösti Albert" },
        detect: false,
      },
    ]);
    // Antwort ohne erkannte Filter: keine Zeile mehr
    await screen.findByRole("heading", { name: "Antwort" });
    expect(screen.queryByText("Gesucht in:")).not.toBeInTheDocument();
  });

  it("bietet bei mehrdeutigem Namen eine Auswahl an", async () => {
    const { user, fetchMock } = await ask(
      "Was sagte Müller zur Stopfleber?",
      AMBIGUOUS,
      DETECTED_ANSWER,
    );
    expect(
      await screen.findByText(
        "Der Name passt auf mehrere Personen; gesucht wurde ohne Personenfilter.",
      ),
    ).toBeInTheDocument();
    await user.click(
      screen.getByRole("button", {
        name: "Nur Voten von Müller Leo (M-E, LU) durchsuchen",
      }),
    );
    expect(askBodies(fetchMock)[1]).toEqual({
      question: "Was sagte Müller zur Stopfleber?",
      filters: { speaker: "Müller Leo" },
    });
  });
});

describe("Datenbestand", () => {
  it("meldet einen Zeitraum ausserhalb in der Sprache der Oberfläche", async () => {
    const { user } = await ask(
      "Was sagte Tamara Funiciello 2022?",
      OUT_OF_RANGE,
    );
    expect(
      await screen.findByRole("heading", {
        name: "Keine Daten zu diesem Zeitraum",
      }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Die Voten reichen vom 4. Dezember 2023 bis 2. Oktober 2026. Fragen Sie nach einem Zeitraum in dieser Spanne.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByText(/Kein KI-Aufruf/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Français" }));
    expect(
      screen.getByRole("heading", { name: "Aucune donnée pour cette période" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/vont du 4 décembre 2023 au 2 octobre 2026/),
    ).toBeInTheDocument();
  });

  it("nennt teilweise Überlappung und die Suche ohne Person", async () => {
    await ask("Was sagte Funiciello seit 2022?", PARTIAL_RETRIED);
    expect(
      await screen.findByText(
        "Die Voten reichen vom 4. Dezember 2023 bis 2. Oktober 2026; für den Rest des Zeitraums gibt es keine Daten.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Zur erkannten Person gab es dazu keine passenden Voten; gezeigt werden Voten aller Personen.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", {
        name: /Filter «seit 01.01.2022» entfernen/,
      }),
    ).toBeInTheDocument();
  });

  it("zeigt bei älteren Antworten ohne die neuen Felder nichts davon", async () => {
    const { filters, coverage, speaker_candidates, retried_without, ...old } =
      DETECTED_ANSWER;
    void [filters, coverage, speaker_candidates, retried_without];
    await ask("Was sagte Rösti?", old);
    await screen.findByRole("heading", { name: "Antwort" });
    expect(screen.queryByText("Gesucht in:")).not.toBeInTheDocument();
  });
});

describe("Feld «Person»", () => {
  it("schickt die gewählte Person mit und zählt sie als aktiven Filter", async () => {
    const fetchMock = apiMock(DETECTED_ANSWER);
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();
    render(<App />);
    await user.type(
      screen.getByLabelText(/Ihre Frage/),
      "Was sagte sie zum Wolf?",
    );
    await user.click(screen.getByRole("button", { name: /^Filter/ }));
    await user.type(screen.getByRole("combobox", { name: "Person" }), "funi");
    await user.keyboard("{Enter}");
    expect(
      screen.getByRole("button", { name: /^Filter/ }),
    ).toHaveAccessibleName("Filter (1 aktiv)");
    expect(
      screen.getByText(
        "Mit Personenfilter werden nur Voten durchsucht, keine Geschäftstexte.",
      ),
    ).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Fragen" }));
    expect(askBodies(fetchMock)).toEqual([
      {
        question: "Was sagte sie zum Wolf?",
        filters: { speaker: "Funiciello Tamara" },
      },
    ]);
  });
});
