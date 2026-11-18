// Darstellung: Zitate im Antworttext, Metadaten der Quellen, Verbrauch.

import type { Source, Usage } from "./api";
import { de, type Messages } from "./i18n/de";

export type Segment =
  { kind: "text"; text: string } | { kind: "cite"; numbers: number[] };

// [3], [1, 2] und [1][2] (Letzteres als zwei Treffer), wie der Server (generation/answer.py).
const CITATION = /\[(\d+(?:\s*,\s*\d+)*)\]/g;

export function splitCitations(answer: string): Segment[] {
  const segments: Segment[] = [];
  let last = 0;
  for (const match of answer.matchAll(CITATION)) {
    const start = match.index ?? 0;
    if (start > last)
      segments.push({ kind: "text", text: answer.slice(last, start) });
    segments.push({
      kind: "cite",
      numbers: match[1].split(",").map((part) => Number(part.trim())),
    });
    last = start + match[0].length;
  }
  if (last < answer.length)
    segments.push({ kind: "text", text: answer.slice(last) });
  return segments;
}

// Kürzel wie in den Daten der Parlamentsdienste; die Namen stehen in den Wörterbüchern (i18n/).
export const COUNCIL_KEYS = ["NR", "SR", "V"] as const;
export const PARL_GROUP_KEYS = ["V", "S", "M-E", "RL", "G", "GL"] as const;

/** Datum als TT.MM.JJJJ (de-CH und fr-CH schreiben es gleich). */
export function formatDate(iso: string, locale = "de-CH"): string {
  const [year, month, day] = iso.split("-").map(Number);
  return new Intl.DateTimeFormat(locale, {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(Date.UTC(year, month - 1, day)));
}

/** Wer: Redner (Fraktion, Kanton) bzw. Bundesrat, oder das Geschäft. */
export function sourceTitle(source: Source, t: Messages = de): string {
  if (source.source_type === "business") {
    const number = source.business_numbers.join(", ");
    return [`${t.source.business} ${number}`.trim(), source.section]
      .filter(Boolean)
      .join(" · ");
  }
  const speaker = source.speaker_name ?? t.source.unknown;
  if (source.speaker_function?.startsWith("B"))
    return `${speaker} (${t.source.federalCouncil})`;
  const details = [source.parl_group, source.canton].filter(Boolean).join(", ");
  return details ? `${speaker} (${details})` : speaker;
}

/** Wo und wann: Rat, Datum, Geschäftsnummer (bei Voten). */
export function sourceContext(source: Source, t: Messages = de): string {
  if (source.source_type === "business") {
    return t.source.submitted(formatDate(source.date, t.locale));
  }
  const councils: Record<string, string> = t.councils;
  return [
    source.council ? (councils[source.council] ?? source.council) : null,
    formatDate(source.date, t.locale),
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

/** Modell, Tokens, Kosten und Dauer der Antwort. */
export function usageLine(usage: Usage, t: Messages = de): string {
  const number = (value: number) => value.toLocaleString(t.locale);
  const seconds = `${(usage.latency_ms / 1000).toFixed(1)} s`;
  if (!usage.model) return `${t.usage.noModel} · ${seconds}`;
  const cost =
    usage.cost_usd == null
      ? t.usage.costUnknown
      : usage.cost_estimated
        ? t.usage.costEstimated(usage.cost_usd.toFixed(4))
        : `${usage.cost_usd.toFixed(4)} USD`;
  return [
    usage.model,
    t.usage.tokens(number(usage.input_tokens), number(usage.output_tokens)),
    cost,
    seconds,
  ].join(" · ");
}
