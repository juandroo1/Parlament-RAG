// Schnittstelle zu `POST /ask` (plan.md, Abschnitt 8; Modelle in `parlrag/api/schemas.py`).

export type Council = "NR" | "SR" | "V";

export interface Filters {
  council?: Council | "";
  date_from?: string;
  date_to?: string;
  parl_group?: string;
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
}

export interface AskRequest {
  question: string;
  filters?: {
    council?: Council;
    date_from?: string;
    date_to?: string;
    parl_group?: string;
  };
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
  ) {
    super(message);
    this.name = "ApiError";
  }
}

/** Anfrage aus Frage und Filtern; leere Filter fallen weg. */
export function buildRequest(question: string, filters: Filters): AskRequest {
  const active: NonNullable<AskRequest["filters"]> = {};
  if (filters.council) active.council = filters.council;
  if (filters.date_from) active.date_from = filters.date_from;
  if (filters.date_to) active.date_to = filters.date_to;
  if (filters.parl_group) active.parl_group = filters.parl_group;
  const request: AskRequest = { question: question.trim() };
  if (Object.keys(active).length > 0) request.filters = active;
  return request;
}

function toError(status: number, body: unknown): ApiError {
  const detail = (body as { detail?: unknown } | null)?.detail;
  if (typeof detail === "string")
    return new ApiError(detail, status, "http", detail);
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
  if (!response.ok) throw toError(response.status, body);
  return body as AskResponse;
}
