import { ApiError } from "../api";
import type { Messages } from "./de";

/**
 * Fehlermeldung in der Sprache der Oberfläche. Meldungen, die die API selbst formuliert (`detail`),
 * kommen bis Task 7.5 noch auf Deutsch.
 */
export function errorText(error: unknown, t: Messages): string {
  if (!(error instanceof ApiError)) return t.errors.unexpected;
  if (error.kind === "network") return t.errors.network;
  if (error.kind === "validation") return t.errors.invalid(error.detail ?? "");
  return error.detail ?? t.errors.http(error.status ?? 0);
}
