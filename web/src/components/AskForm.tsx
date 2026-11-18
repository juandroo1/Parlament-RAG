import { useId, useState } from "react";
import type { Council, Filters } from "../api";
import { COUNCILS, PARL_GROUPS } from "../format";
import { ArrowIcon, FilterIcon } from "./icons";

const EXAMPLES = [
  "Was sagte Bundesrat Rösti zum Kühlwasser der Kernkraftwerke während der Hitzewelle?",
  "Qu'a dit le Conseil fédéral sur la 13e rente AVS au Conseil des Etats ?",
  "Weshalb lehnte der Bundesrat die Landschaftsinitiative ab?",
];

interface Props {
  loading: boolean;
  onSubmit: (question: string, filters: Filters) => void;
}

const field =
  "w-full rounded-[10px] border border-input-border bg-bg px-3 text-text shadow-none " +
  "focus:border-primary focus:outline-none";

export function AskForm({ loading, onSubmit }: Props) {
  const [question, setQuestion] = useState("");
  const [filters, setFilters] = useState<Filters>({});
  const [showFilters, setShowFilters] = useState(false);
  const id = useId();
  const tooShort = question.trim().length < 3;
  const activeFilters = Object.values(filters).filter(Boolean).length;

  const update = (patch: Partial<Filters>) =>
    setFilters((current) => ({ ...current, ...patch }));

  return (
    <form
      className="mt-5 rounded-2xl border border-border bg-surface p-3.5 text-left shadow-card sm:mt-7 sm:p-5"
      onSubmit={(event) => {
        event.preventDefault();
        if (!tooShort && !loading) onSubmit(question, filters);
      }}
    >
      <label
        htmlFor={`${id}-q`}
        className="mb-1.5 block text-sm font-semibold sm:mb-2 sm:text-[15px]"
      >
        Ihre Frage{" "}
        <span className="font-normal text-muted">
          (Deutsch oder Französisch)
        </span>
      </label>
      <textarea
        id={`${id}-q`}
        className={`${field} min-h-24 resize-y rounded-xl py-2.5 text-base leading-normal`}
        rows={3}
        maxLength={500}
        value={question}
        placeholder="z. B. Was sagte der Bundesrat zur Motion …?"
        onChange={(event) => setQuestion(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
            event.currentTarget.form?.requestSubmit();
          }
        }}
      />

      <div className="mt-3">
        <span id={`${id}-ex`} className="text-[13px] text-muted">
          Beispiele:
        </span>
        <ul
          aria-labelledby={`${id}-ex`}
          className="-mx-3.5 mt-1.5 flex gap-2 overflow-x-auto px-3.5 pb-1 sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0"
        >
          {EXAMPLES.map((example) => (
            <li key={example} className="shrink-0 sm:shrink">
              <button
                type="button"
                className="min-h-11 max-w-[260px] rounded-xl border border-border bg-bg px-3.5 py-1.5 text-left text-sm hover:border-primary sm:min-h-9 sm:max-w-none sm:pointer-coarse:min-h-11 sm:rounded-full sm:px-3 sm:py-1 sm:text-[13px]"
                onClick={() => setQuestion(example)}
              >
                {example.length > 60 ? `${example.slice(0, 58)}…` : example}
              </button>
            </li>
          ))}
        </ul>
      </div>

      {showFilters && (
        <fieldset
          id={`${id}-filters`}
          className="mt-4 grid gap-3.5 rounded-xl border border-border p-3.5 sm:grid-cols-2 sm:p-4"
        >
          <legend className="px-1.5 text-[13px] font-semibold">Filter</legend>
          <label className="block text-[13px] font-semibold">
            <span className="mb-1.5 block">Rat</span>
            <select
              className={`${field} h-11`}
              value={filters.council ?? ""}
              onChange={(event) =>
                update({ council: event.target.value as Council | "" })
              }
            >
              <option value="">Alle Räte</option>
              {Object.entries(COUNCILS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="block text-[13px] font-semibold">
            <span className="mb-1.5 block">Fraktion</span>
            <select
              className={`${field} h-11`}
              value={filters.parl_group ?? ""}
              onChange={(event) => update({ parl_group: event.target.value })}
            >
              <option value="">Alle Fraktionen</option>
              {PARL_GROUPS.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            {filters.parl_group && (
              <span className="mt-1.5 block text-xs font-normal text-muted">
                Mit Fraktionsfilter werden nur Voten durchsucht, keine
                Geschäftstexte.
              </span>
            )}
          </label>
          <label className="block text-[13px] font-semibold">
            <span className="mb-1.5 block">Von</span>
            <input
              type="date"
              className={`${field} h-11`}
              value={filters.date_from ?? ""}
              onChange={(event) => update({ date_from: event.target.value })}
            />
          </label>
          <label className="block text-[13px] font-semibold">
            <span className="mb-1.5 block">Bis</span>
            <input
              type="date"
              className={`${field} h-11`}
              value={filters.date_to ?? ""}
              onChange={(event) => update({ date_to: event.target.value })}
            />
          </label>
        </fieldset>
      )}

      <div className="mt-3 flex items-center gap-2 sm:mt-4 sm:justify-between">
        <button
          type="button"
          aria-expanded={showFilters}
          aria-controls={`${id}-filters`}
          className="inline-flex min-h-12 items-center gap-2 rounded-xl border border-border bg-bg px-3.5 text-[15px] font-semibold sm:min-h-11 sm:border-0 sm:bg-transparent sm:px-3 sm:text-sm"
          onClick={() => setShowFilters((value) => !value)}
        >
          <FilterIcon />
          Filter{activeFilters > 0 ? ` (${activeFilters} aktiv)` : ""}
        </button>
        <button
          type="submit"
          disabled={tooShort || loading}
          className="inline-flex min-h-12 flex-1 items-center justify-center gap-2.5 rounded-xl bg-primary px-5 text-base font-bold text-on-primary hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50 sm:flex-none sm:px-6"
        >
          {loading ? "Suche läuft …" : "Fragen"}
          {!loading && <ArrowIcon />}
        </button>
      </div>
    </form>
  );
}
