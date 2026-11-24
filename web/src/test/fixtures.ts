import { vi } from "vitest";
import type { AppliedFilters, AskResponse, Source, Speaker } from "../api";

export const SPEECH: Source = {
  number: 1,
  source_key: "transcript:422528",
  source_type: "transcript",
  language: "de",
  title: "26.9022 Aktuelle Debatte. Hitzewelle und Dürre",
  speaker_name: "Rösti Albert",
  speaker_function: "BR-M",
  parl_group: null,
  canton: "BE",
  council: "NR",
  date: "2026-09-30",
  business_numbers: ["26.9022"],
  section: null,
  text: "Wir brauchen den Strom vor allem im Winter.",
  url: "https://www.parlament.ch/votum47",
};

// Spec 003: Personen und Antworten mit Erkennung
export const SPEAKERS: Speaker[] = [
  {
    name: "Aebischer Matthias",
    parl_group: "S",
    canton: "BE",
    council: "NR",
    federal_council: false,
    votes: 40,
  },
  {
    name: "Funiciello Tamara",
    parl_group: "S",
    canton: "BE",
    council: "NR",
    federal_council: false,
    votes: 119,
  },
  {
    name: "Müller Damian",
    parl_group: "RL",
    canton: "LU",
    council: "SR",
    federal_council: false,
    votes: 173,
  },
  {
    name: "Müller Leo",
    parl_group: "M-E",
    canton: "LU",
    council: "NR",
    federal_council: false,
    votes: 82,
  },
  {
    name: "Rösti Albert",
    parl_group: null,
    canton: "BE",
    council: "SR",
    federal_council: true,
    votes: 1218,
  },
  {
    name: "Schneider Meret",
    parl_group: "G",
    canton: "ZH",
    council: "NR",
    federal_council: false,
    votes: 55,
  },
];

export function applied(
  values: Partial<AppliedFilters["applied"]>,
  detected: string[] = [],
): AppliedFilters {
  return {
    applied: {
      council: null,
      date_from: null,
      date_to: null,
      parl_group: null,
      speaker: null,
      ...values,
    },
    detected,
  };
}

export const COVERAGE = {
  first: "2023-12-04",
  last: "2026-10-02",
  partial: false,
};

export const DETECTED_ANSWER: AskResponse = {
  answer: "Rösti betonte den Winterstrom [1].",
  insufficient_context: false,
  insufficient_reason: null,
  sources: [SPEECH],
  usage: {
    model: "claude-haiku-5-5",
    backend: "api",
    input_tokens: 9100,
    output_tokens: 1300,
    cost_usd: 0.0016,
    cost_estimated: false,
    latency_ms: 6040,
  },
  filters: applied(
    { speaker: "Rösti Albert", date_from: "2025-01-01", date_to: "2025-12-31" },
    ["speaker", "date_from", "date_to"],
  ),
  coverage: COVERAGE,
  speaker_candidates: [],
  retried_without: [],
};

export const OUT_OF_RANGE: AskResponse = {
  ...DETECTED_ANSWER,
  answer: "Zu diesem Zeitraum gibt es keine Daten.",
  insufficient_context: true,
  insufficient_reason: "out_of_range",
  sources: [],
  usage: {
    ...DETECTED_ANSWER.usage,
    model: null,
    backend: null,
    input_tokens: 0,
    output_tokens: 0,
    cost_usd: 0,
    latency_ms: 95,
  },
  filters: applied(
    {
      speaker: "Funiciello Tamara",
      date_from: "2022-01-01",
      date_to: "2022-12-31",
    },
    ["speaker", "date_from", "date_to"],
  ),
};

export const AMBIGUOUS: AskResponse = {
  ...DETECTED_ANSWER,
  filters: applied({}),
  speaker_candidates: SPEAKERS.filter((s) => s.name.startsWith("Müller")),
};

export const PARTIAL_RETRIED: AskResponse = {
  ...DETECTED_ANSWER,
  filters: applied({ date_from: "2022-01-01" }, ["date_from"]),
  coverage: { ...COVERAGE, partial: true },
  retried_without: ["speaker"],
};

/** fetch-Attrappe: `/api/speakers` liefert SPEAKERS, `/api/ask` der Reihe nach die Antworten. */
export function apiMock(...answers: AskResponse[]) {
  const queue = [...answers];
  return vi.fn((url: string, _init?: RequestInit) => {
    const body =
      url === "/api/speakers"
        ? SPEAKERS
        : queue.length > 1
          ? queue.shift()
          : queue[0];
    return Promise.resolve({
      ok: true,
      status: 200,
      headers: new Headers(),
      json: () => Promise.resolve(body),
    });
  });
}
