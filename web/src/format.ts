// Darstellung: Zitate im Antworttext, Metadaten der Quellen, Verbrauch.

import type { Source, Usage } from "./api";

export type Segment = { kind: "text"; text: string } | { kind: "cite"; numbers: number[] };

// [3], [1, 2] und [1][2] (Letzteres als zwei Treffer), wie der Server (generation/answer.py).
const CITATION = /\[(\d+(?:\s*,\s*\d+)*)\]/g;

export function splitCitations(answer: string): Segment[] {
  const segments: Segment[] = [];
  let last = 0;
  for (const match of answer.matchAll(CITATION)) {
    const start = match.index ?? 0;
    if (start > last) segments.push({ kind: "text", text: answer.slice(last, start) });
    segments.push({ kind: "cite", numbers: match[1].split(",").map((part) => Number(part.trim())) });
    last = start + match[0].length;
  }
  if (last < answer.length) segments.push({ kind: "text", text: answer.slice(last) });
  return segments;
}

export const COUNCILS: Record<string, string> = {
  NR: "Nationalrat",
  SR: "Ständerat",
  V: "Vereinigte Bundesversammlung",
};

// Fraktionen der 52. Legislatur (Kürzel wie in den Daten der Parlamentsdienste).
export const PARL_GROUPS: [string, string][] = [
  ["V", "SVP-Fraktion"],
  ["S", "Sozialdemokratische Fraktion"],
  ["M-E", "Mitte-Fraktion"],
  ["RL", "FDP-Liberale Fraktion"],
  ["G", "Grüne Fraktion"],
  ["GL", "Grünliberale Fraktion"],
];

export function formatDate(iso: string): string {
  const [year, month, day] = iso.split("-");
  return `${day}.${month}.${year}`;
}

/** Wer: Redner (Fraktion, Kanton) bzw. Bundesrat, oder das Geschäft. */
export function sourceTitle(source: Source): string {
  if (source.source_type === "business") {
    const number = source.business_numbers.join(", ");
    return [`Geschäft ${number}`.trim(), source.section].filter(Boolean).join(" · ");
  }
  const speaker = source.speaker_name ?? "Unbekannt";
  if (source.speaker_function?.startsWith("B")) return `${speaker} (Bundesrat)`;
  const details = [source.parl_group, source.canton].filter(Boolean).join(", ");
  return details ? `${speaker} (${details})` : speaker;
}

/** Wo und wann: Rat, Datum, Geschäftsnummer (bei Voten). */
export function sourceContext(source: Source): string {
  if (source.source_type === "business") return `eingereicht ${formatDate(source.date)}`;
  return [
    source.council ? (COUNCILS[source.council] ?? source.council) : null,
    formatDate(source.date),
    source.business_numbers.join(", ") || null,
  ]
    .filter(Boolean)
    .join(" · ");
}

export function snippet(text: string, limit = 280): string {
  const flat = text.split(/\s+/).join(" ").trim();
  if (flat.length <= limit) return flat;
  return `${flat.slice(0, limit).replace(/\s+\S*$/, "")} …`;
}

function number(value: number): string {
  return value.toLocaleString("de-CH");
}

export function usageLine(usage: Usage): string {
  const seconds = `${(usage.latency_ms / 1000).toFixed(1)} s`;
  if (!usage.model) return `Kein KI-Aufruf · ${seconds}`;
  const cost =
    usage.cost_usd == null
      ? "Kosten unbekannt"
      : usage.cost_estimated
        ? `≈ ${usage.cost_usd.toFixed(4)} USD geschätzt, im Claude-Abo enthalten`
        : `${usage.cost_usd.toFixed(4)} USD`;
  return [
    usage.model,
    `${number(usage.input_tokens)} Input- und ${number(usage.output_tokens)} Output-Tokens`,
    cost,
    seconds,
  ].join(" · ");
}
