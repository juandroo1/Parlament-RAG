import { useId, useState } from "react";
import type { Council, Filters } from "../api";
import { COUNCILS, PARL_GROUPS } from "../format";

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
  "w-full rounded-md border border-slate-300 bg-white px-3 py-2 text-slate-900 shadow-sm " +
  "focus:border-red-700 focus:ring-2 focus:ring-red-700/30 focus:outline-none " +
  "dark:border-slate-600 dark:bg-slate-900 dark:text-slate-100";

export function AskForm({ loading, onSubmit }: Props) {
  const [question, setQuestion] = useState("");
  const [filters, setFilters] = useState<Filters>({});
  const [showFilters, setShowFilters] = useState(false);
  const id = useId();
  const tooShort = question.trim().length < 3;
  const activeFilters = Object.values(filters).filter(Boolean).length;

  const update = (patch: Partial<Filters>) => setFilters((current) => ({ ...current, ...patch }));

  return (
    <form
      className="space-y-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (!tooShort && !loading) onSubmit(question, filters);
      }}
    >
      <div>
        <label htmlFor={`${id}-q`} className="mb-1 block font-medium">
          Ihre Frage <span className="font-normal text-slate-500">(Deutsch oder Französisch)</span>
        </label>
        <textarea
          id={`${id}-q`}
          className={`${field} min-h-24`}
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
        <div className="mt-2 flex flex-wrap gap-2 text-sm">
          <span className="text-slate-500">Beispiele:</span>
          {EXAMPLES.map((example) => (
            <button
              key={example}
              type="button"
              className="rounded-full border border-slate-300 px-3 py-0.5 text-left hover:border-red-700 hover:text-red-800 dark:border-slate-600 dark:hover:text-red-300"
              onClick={() => setQuestion(example)}
            >
              {example.length > 60 ? `${example.slice(0, 58)}…` : example}
            </button>
          ))}
        </div>
      </div>

      <div>
        <button
          type="button"
          aria-expanded={showFilters}
          aria-controls={`${id}-filters`}
          className="text-sm font-medium text-red-800 hover:underline dark:text-red-300"
          onClick={() => setShowFilters((value) => !value)}
        >
          {showFilters ? "▾" : "▸"} Filter{activeFilters > 0 ? ` (${activeFilters} aktiv)` : ""}
        </button>
        {showFilters && (
          <fieldset
            id={`${id}-filters`}
            className="mt-3 grid gap-4 rounded-lg border border-slate-200 p-4 sm:grid-cols-2 dark:border-slate-700"
          >
            <legend className="sr-only">Filter</legend>
            <label className="block text-sm">
              <span className="mb-1 block font-medium">Rat</span>
              <select
                className={field}
                value={filters.council ?? ""}
                onChange={(event) => update({ council: event.target.value as Council | "" })}
              >
                <option value="">Alle Räte</option>
                {Object.entries(COUNCILS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium">Fraktion</span>
              <select
                className={field}
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
                <span className="mt-1 block text-xs text-slate-500">
                  Mit Fraktionsfilter werden nur Voten durchsucht, keine Geschäftstexte.
                </span>
              )}
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium">Von</span>
              <input
                type="date"
                className={field}
                value={filters.date_from ?? ""}
                onChange={(event) => update({ date_from: event.target.value })}
              />
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium">Bis</span>
              <input
                type="date"
                className={field}
                value={filters.date_to ?? ""}
                onChange={(event) => update({ date_to: event.target.value })}
              />
            </label>
          </fieldset>
        )}
      </div>

      <button
        type="submit"
        disabled={tooShort || loading}
        className="rounded-md bg-red-700 px-5 py-2 font-semibold text-white shadow-sm hover:bg-red-800 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {loading ? "Suche läuft …" : "Fragen"}
      </button>
    </form>
  );
}
