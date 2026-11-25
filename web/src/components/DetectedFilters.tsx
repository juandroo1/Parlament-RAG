import type { AskResponse, Filters } from "../api";
import { periodLabel, speakerLabel } from "../format";
import { useI18n } from "../i18n/LanguageProvider";
import { CloseIcon } from "./icons";

interface Props {
  result: AskResponse;
  /** Erkannte Filter entfernen und ohne Erkennung neu fragen (AK-17.5). */
  onRemove: (keys: (keyof Filters)[]) => void;
  /** Bei einem mehrdeutigen Namen mit dieser Person neu fragen (AK-17.3). */
  onChoose: (name: string) => void;
}

const pill =
  "inline-flex min-h-9 items-center gap-1.5 rounded-full border border-border bg-bg px-3 text-[13px] " +
  "hover:border-primary pointer-coarse:min-h-11";

/** Zeile über der Antwort: aus der Frage erkannte Filter und Kandidaten bei mehrdeutigem Namen
 * (Spec 003, plan.md Abschnitt 9). */
export function DetectedFilters({ result, onRemove, onChoose }: Props) {
  const { t } = useI18n();
  const detected = result.filters?.detected ?? [];
  const applied = result.filters?.applied;
  const candidates = result.speaker_candidates ?? [];

  const chips: { label: string; keys: (keyof Filters)[] }[] = [];
  if (applied && detected.includes("speaker") && applied.speaker) {
    chips.push({
      label: t.detected.speaker(applied.speaker),
      keys: ["speaker"],
    });
  }
  if (
    applied &&
    (detected.includes("date_from") || detected.includes("date_to"))
  ) {
    chips.push({
      label: periodLabel(applied.date_from, applied.date_to, t),
      keys: ["date_from", "date_to"],
    });
  }
  if (chips.length === 0 && candidates.length === 0) return null;

  return (
    <div className="mb-6 space-y-3 text-sm">
      {chips.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-muted">{t.detected.label}</span>
          {chips.map((chip) => (
            <button
              key={chip.label}
              type="button"
              aria-label={t.detected.remove(chip.label)}
              title={t.detected.remove(chip.label)}
              className={pill}
              onClick={() => onRemove(chip.keys)}
            >
              <span className="font-semibold">{chip.label}</span>
              <CloseIcon />
            </button>
          ))}
        </div>
      )}
      {candidates.length > 0 && (
        <div>
          <p className="text-muted">{t.detected.candidatesHint}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <span className="font-semibold">{t.detected.candidates}</span>
            {candidates.map((speaker) => (
              <button
                key={speaker.name}
                type="button"
                aria-label={t.detected.choose(speakerLabel(speaker, t))}
                className={pill}
                onClick={() => onChoose(speaker.name)}
              >
                {speakerLabel(speaker, t)}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
