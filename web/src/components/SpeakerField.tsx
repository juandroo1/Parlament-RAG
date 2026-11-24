import { useEffect, useId, useMemo, useState } from "react";
import { fetchSpeakers, type Speaker } from "../api";
import { fold, speakerLabel } from "../format";
import { useI18n } from "../i18n/LanguageProvider";
import { CloseIcon } from "./icons";

interface Props {
  value?: string;
  onChange: (name: string | undefined) => void;
  className: string;
}

const MAX_SUGGESTIONS = 8;

/** Personen, deren Name alle eingegebenen Wörter enthält; Treffer am Wortanfang zuerst
 * («sch» zeigt «Schneider Meret» vor «Aebischer Matthias»), sonst alphabetisch. */
export function suggest(speakers: Speaker[], text: string): Speaker[] {
  const words = fold(text).split(/\s+/).filter(Boolean);
  if (words.length === 0) return [];
  const scored: { speaker: Speaker; prefix: number }[] = [];
  for (const speaker of speakers) {
    const name = fold(speaker.name);
    if (!words.every((word) => name.includes(word))) continue;
    const parts = name.split(/[\s-]+/);
    const prefix = words.filter((word) =>
      parts.some((part) => part.startsWith(word)),
    ).length;
    scored.push({ speaker, prefix });
  }
  return scored
    .sort((a, b) => b.prefix - a.prefix)
    .slice(0, MAX_SUGGESTIONS)
    .map((entry) => entry.speaker);
}

/**
 * Feld «Person» mit Vorschlägen (Spec 003, AK-18.1), nach dem ARIA-Muster «Combobox»:
 * Pfeiltasten wählen, Enter übernimmt, Esc schliesst. Die Liste kommt aus `GET /speakers` und
 * wird beim ersten Fokus geladen. Gültig sind nur Namen aus der Liste; freier Text ohne Auswahl
 * wird beim Verlassen verworfen.
 */
export function SpeakerField({ value, onChange, className }: Props) {
  const { t } = useI18n();
  const id = useId();
  const listId = `${id}-list`;
  const [text, setText] = useState(value ?? "");
  const [speakers, setSpeakers] = useState<Speaker[] | null>(null);
  const [status, setStatus] = useState<"idle" | "loading" | "error">("idle");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);

  useEffect(() => setText(value ?? ""), [value]);

  const load = () => {
    if (speakers || status === "loading") return;
    setStatus("loading");
    fetchSpeakers()
      .then((list) => {
        setSpeakers(list);
        setStatus("idle");
      })
      .catch(() => setStatus("error"));
  };

  const matches = useMemo(
    () => (text === value ? [] : suggest(speakers ?? [], text)),
    [speakers, text, value],
  );

  const showList = open && matches.length > 0;
  const message =
    open && text.trim() && text !== value
      ? status === "loading"
        ? t.form.personLoading
        : status === "error"
          ? t.form.personError
          : speakers && matches.length === 0
            ? t.form.personNone
            : null
      : null;

  const select = (speaker: Speaker) => {
    onChange(speaker.name);
    setText(speaker.name);
    setOpen(false);
  };

  return (
    <div className="relative">
      <div className="relative">
        <input
          id={`${id}-input`}
          role="combobox"
          aria-autocomplete="list"
          aria-expanded={showList}
          aria-controls={listId}
          aria-activedescendant={
            showList ? `${id}-option-${active}` : undefined
          }
          aria-label={t.form.person}
          autoComplete="off"
          spellCheck={false}
          className={`${className} ${value ? "pr-11" : ""}`}
          placeholder={t.form.personPlaceholder}
          value={text}
          onFocus={load}
          onChange={(event) => {
            setText(event.target.value);
            setOpen(true);
            setActive(0);
            if (value) onChange(undefined);
            load();
          }}
          onBlur={() => {
            setOpen(false);
            if (text === value) return;
            const exact = speakers?.find(
              (s) => fold(s.name) === fold(text.trim()),
            );
            if (exact) select(exact);
            else setText(value ?? "");
          }}
          onKeyDown={(event) => {
            if (event.key === "ArrowDown") {
              event.preventDefault();
              setOpen(true);
              setActive((current) =>
                Math.min(current + 1, Math.max(matches.length - 1, 0)),
              );
            } else if (event.key === "ArrowUp") {
              event.preventDefault();
              setActive((current) => Math.max(current - 1, 0));
            } else if (event.key === "Enter" && showList) {
              event.preventDefault(); // nicht das Formular absenden
              select(matches[active]);
            } else if (event.key === "Escape" && open) {
              event.preventDefault();
              setOpen(false);
            }
          }}
        />
        {value && (
          <button
            type="button"
            aria-label={t.form.personClear}
            title={t.form.personClear}
            className="absolute top-0 right-0 flex h-full w-11 items-center justify-center text-muted hover:text-text"
            onClick={() => {
              onChange(undefined);
              setText("");
            }}
          >
            <CloseIcon />
          </button>
        )}
      </div>
      <ul
        id={listId}
        role="listbox"
        aria-label={t.form.person}
        hidden={!showList}
        className="absolute inset-x-0 top-full z-10 mt-1 max-h-72 overflow-auto rounded-xl border border-border bg-surface py-1 shadow-card"
      >
        {matches.map((speaker, index) => (
          <li
            key={speaker.name}
            id={`${id}-option-${index}`}
            role="option"
            aria-selected={index === active}
            className={`cursor-pointer px-3 py-2.5 text-sm font-normal ${index === active ? "bg-surface-2" : ""}`}
            // mousedown statt click: der Fokus bleibt im Feld, onBlur verwirft nichts
            onMouseDown={(event) => {
              event.preventDefault();
              select(speaker);
            }}
            onMouseEnter={() => setActive(index)}
          >
            {speakerLabel(speaker, t)}
          </li>
        ))}
      </ul>
      <p
        aria-live="polite"
        className="mt-1.5 text-xs font-normal text-muted empty:mt-0"
      >
        {message}
      </p>
    </div>
  );
}
