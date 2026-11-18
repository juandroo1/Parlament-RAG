import { ApiError } from "../api";
import type { Messages } from "./de";

/** Wartezeit in ganzen Minuten, aufgerundet, mindestens 1. */
export function minutes(seconds: number | null): number {
  return Math.max(1, Math.ceil((seconds ?? 60) / 60));
}

/**
 * Fehlermeldung in der Sprache der Oberfläche (AK-10.3). Bei einem bekannten Fehlercode der API
 * (`X-Error-Code`) die übersetzte Meldung, sonst die Meldung der API (`detail`) oder eine
 * allgemeine Meldung mit dem HTTP-Status.
 */
export function errorText(error: unknown, t: Messages): string {
  if (!(error instanceof ApiError)) return t.errors.unexpected;
  if (error.kind === "network") return t.errors.network;
  if (error.kind === "validation") return t.errors.invalid(error.detail ?? "");
  const coded =
    error.code && Object.hasOwn(t.errors.codes, error.code)
      ? t.errors.codes[error.code]
      : undefined;
  if (coded) return coded(minutes(error.retryAfter));
  return error.detail ?? t.errors.http(error.status ?? 0);
}
