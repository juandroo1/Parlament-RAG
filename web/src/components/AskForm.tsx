import { useId, useState } from "react";
import type { Council, Filters } from "../api";
import { COUNCIL_KEYS, PARL_GROUP_KEYS } from "../format";
import { useI18n } from "../i18n/LanguageProvider";
import { ArrowIcon, ChevronIcon, FilterIcon } from "./icons";

interface Props {
  loading: boolean;
  onSubmit: (question: string, filters: Filters) => void;
}

const field =
  "w-full rounded-[10px] border border-input-border bg-bg px-3 text-text shadow-none " +
  "focus:border-primary focus:outline-none";

export function AskForm({ loading, onSubmit }: Props) {
  const { t } = useI18n();
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
        {t.form.label}{" "}
        <span className="font-normal text-muted">{t.form.hint}</span>
      </label>
      <textarea
        id={`${id}-q`}
        className={`${field} min-h-24 resize-y rounded-xl py-2.5 text-base leading-normal`}
        rows={3}
        maxLength={500}
        value={question}
        placeholder={t.form.placeholder}
        onChange={(event) => setQuestion(event.target.value)}
        onKeyDown={(event) => {
          if (event.key === "Enter" && (event.ctrlKey || event.metaKey)) {
            event.currentTarget.form?.requestSubmit();
          }
        }}
      />

      {/* Beispiele und Filter-Pille (Entwurf B, AK-15.1). Die Pille steht rechts neben «Beispiele:»,
          die Beispiele darunter über die volle Breite (Handy: zum Wischen). Das Grid ordnet an, die
          Reihenfolge im HTML bleibt Beispiele → Filter → Fragen. */}
      <div className="mt-3 grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-3 gap-y-1.5">
        <span
          id={`${id}-ex`}
          className="col-start-1 row-start-1 text-[13px] text-muted"
        >
          {t.form.examples}
        </span>
        <ul
          aria-labelledby={`${id}-ex`}
          className="col-span-2 row-start-2 -mx-3.5 flex gap-2 overflow-x-auto px-3.5 pb-1 sm:mx-0 sm:flex-wrap sm:overflow-visible sm:px-0 sm:pb-0"
        >
          {t.form.exampleQuestions.map(({ text: example, lang }) => (
            <li key={example} className="shrink-0 sm:shrink">
              <button
                type="button"
                className="min-h-11 max-w-[260px] rounded-xl border border-border bg-bg px-3.5 py-1.5 text-left text-sm hover:border-primary sm:min-h-9 sm:max-w-none sm:pointer-coarse:min-h-11 sm:rounded-full sm:px-3 sm:py-1 sm:text-[13px]"
                lang={lang}
                onClick={() => setQuestion(example)}
              >
                {example.length > 60 ? `${example.slice(0, 58)}…` : example}
              </button>
            </li>
          ))}
        </ul>
        <button
          type="button"
          aria-expanded={showFilters}
          aria-controls={`${id}-filters`}
          className={`col-start-2 row-start-1 inline-flex min-h-11 items-center gap-2 justify-self-end rounded-full border bg-bg px-3.5 text-sm font-semibold hover:border-primary sm:min-h-9 sm:pointer-coarse:min-h-11 sm:px-3 sm:text-[13px] ${showFilters ? "border-primary" : "border-border"}`}
          onClick={() => setShowFilters((value) => !value)}
        >
          <FilterIcon />
          {t.form.filter}
          {activeFilters > 0 && (
            <>
              <span
                aria-hidden="true"
                className="inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-primary px-1.5 text-xs font-bold text-on-primary"
              >
                {activeFilters}
              </span>
              <span className="sr-only">
                , {t.form.activeFilters(activeFilters)}
              </span>
            </>
          )}
          <span
            className={`transition-transform duration-200 ${showFilters ? "rotate-180" : ""}`}
          >
            <ChevronIcon />
          </span>
        </button>
      </div>

      {/* Auf- und Zuklappen mit Grid-Zeilen 0fr ↔ 1fr (AK-15.2); bei reduzierter Bewegung schaltet die
          globale Regel in theme.css den Übergang ab. Zugeklappt ist der Bereich «inert»: weder per
          Tastatur noch für Screenreader erreichbar. */}
      <div
        data-testid="filter-panel"
        className={`grid transition-[grid-template-rows] duration-200 ease-out ${showFilters ? "grid-rows-[1fr]" : "grid-rows-[0fr]"}`}
      >
        <div className="min-h-0 overflow-hidden" inert={!showFilters}>
          <fieldset
            id={`${id}-filters`}
            className="mt-4 grid gap-3.5 rounded-xl border border-border p-3.5 sm:grid-cols-2 sm:p-4 md:grid-cols-[minmax(0,1.3fr)_minmax(0,1.3fr)_minmax(0,1fr)_minmax(0,1fr)]"
          >
              <legend className="px-1.5 text-[13px] font-semibold">
                {t.form.filter}
              </legend>
              <label className="block text-[13px] font-semibold">
                <span className="mb-1.5 block">{t.form.council}</span>
                <select
                  className={`${field} h-11`}
                  value={filters.council ?? ""}
                  onChange={(event) =>
                    update({ council: event.target.value as Council | "" })
                  }
                >
                  <option value="">{t.form.allCouncils}</option>
                  {COUNCIL_KEYS.map((value) => (
                    <option key={value} value={value}>
                      {t.councils[value]}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-[13px] font-semibold">
                <span className="mb-1.5 block">{t.form.group}</span>
                <select
                  className={`${field} h-11`}
                  value={filters.parl_group ?? ""}
                  onChange={(event) => update({ parl_group: event.target.value })}
                >
                  <option value="">{t.form.allGroups}</option>
                  {PARL_GROUP_KEYS.map((value) => (
                    <option key={value} value={value}>
                      {t.parlGroups[value]}
                    </option>
                  ))}
                </select>
                {filters.parl_group && (
                  <span className="mt-1.5 block text-xs font-normal text-muted">
                    {t.form.groupNote}
                  </span>
                )}
              </label>
              <label className="block text-[13px] font-semibold">
                <span className="mb-1.5 block">{t.form.from}</span>
                <input
                  type="date"
                  className={`${field} h-11`}
                  value={filters.date_from ?? ""}
                  onChange={(event) => update({ date_from: event.target.value })}
                />
              </label>
              <label className="block text-[13px] font-semibold">
                <span className="mb-1.5 block">{t.form.to}</span>
                <input
                  type="date"
                  className={`${field} h-11`}
                  value={filters.date_to ?? ""}
                  onChange={(event) => update({ date_to: event.target.value })}
                />
              </label>
          </fieldset>
        </div>
      </div>

      <div className="mt-3 flex sm:mt-4 sm:justify-end">
        <button
          type="submit"
          disabled={tooShort || loading}
          className="inline-flex min-h-12 flex-1 items-center justify-center gap-2.5 rounded-xl bg-primary px-5 text-base font-bold text-on-primary hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50 sm:flex-none sm:px-6"
        >
          {loading ? t.form.searching : t.form.submit}
          {!loading && <ArrowIcon />}
        </button>
      </div>
    </form>
  );
}
