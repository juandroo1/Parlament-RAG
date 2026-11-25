// Schnittstelle zu `POST /ask` (plan.md, Abschnitt 8; Modelle in `parlrag/api/schemas.py`).

export type Council = "NR" | "SR" | "V";

export interface Filters {
  council?: Council | "";
  date_from?: string;
  date_to?: string;
  parl_group?: string;
  /** Name wie in den Daten, «Nachname Vorname» (Spec 003, AK-18.2). */
  speaker?: string;
}

/** Person mit Voten aus `GET /speakers` (Spec 003, AK-18.1). */
export interface Speaker {
  name: string;
  parl_group: string | null;
  canton: string | null;
  council: string | null;
  federal_council: boolean;
  votes: number;
}

/** Abgedeckter Zeitraum der Voten; `partial`, wenn die Frage darüber hinausgeht (AK-16.2). */
export interface Coverage {
  first: string;
  last: string;
  partial: boolean;
}

/** Filter der Suche (gesetzt plus erkannt) und welche davon erkannt wurden (AK-17.5). */
export interface AppliedFilters {
  applied: {
    council: Council | null;
    date_from: string | null;
    date_to: string | null;
    parl_group: string | null;
    speaker: string | null;
  };
  detected: string[];
}

export interface Source {
  number: number;
  source_key: string;
  source_type: "transcript" | "business" | string;
  language: string;
  title: string;
  speaker_name: string | null;
  speaker_function: string | null;
  parl_group: string | null;
  canton: string | null;
  council: string | null;
  date: string;
  business_numbers: string[];
  section: string | null;
  text: string;
  url: string;
}

export interface Usage {
  model: string | null;
  backend: string | null;
  input_tokens: number;
  output_tokens: number;
  cost_usd: number | null;
  cost_estimated: boolean;
  latency_ms: number;
}

export interface AskResponse {
  answer: string;
  insufficient_context: boolean;
  insufficient_reason: string | null;
  sources: Source[];
  usage: Usage;
  // Seit Spec 003; optional, damit ältere Antworten gültig bleiben.
  filters?: AppliedFilters;
  coverage?: Coverage | null;
  speaker_candidates?: Speaker[];
  retried_without?: string[];
}

export interface AskRequest {
  question: string;
  filters?: {
    council?: Council;
    date_from?: string;
    date_to?: string;
    parl_group?: string;
    speaker?: string;
  };
  /** false: Person und Zeitraum nicht aus der Frage erkennen (Standard true). */
  detect?: boolean;
}

/** Art des Fehlers; die Oberfläche formuliert daraus die Meldung in ihrer Sprache (Task 7.4). */
export type ApiErrorKind = "network" | "validation" | "http";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number | null,
    readonly kind: ApiErrorKind = "http",
    /** Meldung der API (`detail`) bzw. bei Validierungsfehlern die Liste der Felder. */
    readonly detail: string | null = null,
    /** Fehlercode aus `X-Error-Code` (Task 7.5), z. B. `rate_limit`. */
    readonly code: string | null = null,
    /** Wartezeit in Sekunden aus `Retry-After`. */
    readonly retryAfter: number | null = null,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Anfrage aus Frage und Filtern; leere Filter fallen weg, `detect` nur wenn ausgeschaltet. */
export function buildRequest(
  question: string,
  filters: Filters,
  detect = true,
): AskRequest {
  const active: NonNullable<AskRequest["filters"]> = {};
  if (filters.council) active.council = filters.council;
  if (filters.date_from) active.date_from = filters.date_from;
  if (filters.date_to) active.date_to = filters.date_to;
  if (filters.parl_group) active.parl_group = filters.parl_group;
  if (filters.speaker) active.speaker = filters.speaker;
  const request: AskRequest = { question: question.trim() };
  if (Object.keys(active).length > 0) request.filters = active;
  if (!detect) request.detect = false;
  return request;
}

/** Angewandte Filter der Antwort als Filter für eine neue Anfrage, ohne die genannten. */
export function filtersFrom(
  applied: AppliedFilters["applied"],
  without: (keyof Filters)[] = [],
): Filters {
  const filters: Filters = {};
  for (const [key, value] of Object.entries(applied) as [
    keyof Filters,
    string | null,
  ][]) {
    if (value && !without.includes(key))
      (filters as Record<string, string>)[key] = value;
  }
  return filters;
}

let speakersRequest: Promise<Speaker[]> | null = null;

/** Personen für das Feld «Person»; einmal pro Sitzung geladen, nach einem Fehler erneut. */
export function fetchSpeakers(
  fetchImpl: typeof fetch = fetch,
): Promise<Speaker[]> {
  speakersRequest ??= fetchImpl("/api/speakers")
    .then((response) => {
      if (!response.ok)
        throw new ApiError(`HTTP ${response.status}`, response.status);
      return response.json() as Promise<Speaker[]>;
    })
    .catch((error: unknown) => {
      speakersRequest = null;
      throw error;
    });
  return speakersRequest;
}

/** Nur für Tests: zwischengespeicherte Personen vergessen. */
export function resetSpeakers(): void {
  speakersRequest = null;
}

/** Header einer Antwort lesen; Attrappen in Tests haben eventuell keine. */
function header(response: Response, name: string): string | null {
  return response.headers?.get?.(name) ?? null;
}

function toError(response: Response, body: unknown): ApiError {
  const status = response.status;
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string") {
    const seconds = Number(header(response, "Retry-After"));
    return new ApiError(
      detail,
      status,
      "http",
      detail,
      header(response, "X-Error-Code"),
      Number.isFinite(seconds) && seconds > 0 ? seconds : null,
    );
  }
  if (status === 422 && Array.isArray(detail)) {
    const fields = detail
      .map((item) => (item as { msg?: string }).msg)
      .filter(Boolean)
      .join("; ");
    return new ApiError(
      `Die Eingabe ist ungültig${fields ? `: ${fields}` : "."}`,
      status,
      "validation",
      fields,
    );
  }
  return new ApiError(
    `Die Anfrage ist fehlgeschlagen (HTTP ${status}).`,
    status,
  );
}

export async function ask(
  request: AskRequest,
  fetchImpl: typeof fetch = fetch,
): Promise<AskResponse> {
  let response: Response;
  try {
    response = await fetchImpl("/api/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request),
    });
  } catch {
    throw new ApiError(
      "Die API ist nicht erreichbar. Läuft der Server?",
      null,
      "network",
    );
  }
  const body: unknown = await response.json().catch(() => null);
  if (!response.ok) throw toError(response, body);
  return body as AskResponse;
}
