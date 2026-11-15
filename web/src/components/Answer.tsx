import { useEffect, useRef, useState } from "react";
import type { AskResponse } from "../api";
import { splitCitations, usageLine } from "../format";
import { SourceCard } from "./SourceCard";

const REASONS: Record<string, string> = {
  no_hits: "Die Suche fand keine passenden Abschnitte.",
  low_similarity: "Die gefundenen Abschnitte passen zu wenig zur Frage.",
  model: "Die gefundenen Abschnitte beantworten die Frage nicht.",
};

export function Answer({ result }: { result: AskResponse }) {
  const [highlighted, setHighlighted] = useState<number | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const numbers = new Set(result.sources.map((source) => source.number));

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const jumpTo = (number: number) => {
    const element = document.getElementById(`quelle-${number}`);
    element?.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
    element?.focus({ preventScroll: true });
    setHighlighted(number);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setHighlighted(null), 2000);
  };

  if (result.insufficient_context) {
    return (
      <section
        aria-live="polite"
        className="rounded-lg border border-amber-300 bg-amber-50 p-5 dark:border-amber-700 dark:bg-amber-950/40"
      >
        <h2 className="font-semibold">Keine ausreichende Grundlage</h2>
        <p className="mt-2">{result.answer}</p>
        {result.insufficient_reason && REASONS[result.insufficient_reason] && (
          <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
            {REASONS[result.insufficient_reason]} Versuchen Sie eine konkretere Frage oder andere
            Filter.
          </p>
        )}
        <p className="mt-3 text-xs text-slate-500">{usageLine(result.usage)}</p>
      </section>
    );
  }

  return (
    <section aria-live="polite" className="space-y-6">
      <div>
        <h2 className="mb-2 text-lg font-semibold">Antwort</h2>
        <p className="leading-relaxed whitespace-pre-line">
          {splitCitations(result.answer).map((segment, index) =>
            segment.kind === "text" ? (
              <span key={index}>{segment.text}</span>
            ) : (
              <span key={index}>
                {segment.numbers.map((number) =>
                  numbers.has(number) ? (
                    <a
                      key={number}
                      href={`#quelle-${number}`}
                      aria-label={`Quelle ${number}`}
                      className="mx-px rounded px-0.5 align-super text-xs font-semibold text-red-800 hover:bg-red-50 dark:text-red-300 dark:hover:bg-red-950"
                      onClick={(event) => {
                        event.preventDefault();
                        jumpTo(number);
                      }}
                    >
                      [{number}]
                    </a>
                  ) : (
                    <span key={number} className="align-super text-xs">
                      [{number}]
                    </span>
                  ),
                )}
              </span>
            ),
          )}
        </p>
        <p className="mt-3 text-xs text-slate-500">{usageLine(result.usage)}</p>
      </div>
      <div>
        <h2 className="mb-2 text-lg font-semibold">Quellen</h2>
        <ol className="space-y-3">
          {result.sources.map((source) => (
            <SourceCard
              key={source.number}
              source={source}
              highlighted={highlighted === source.number}
            />
          ))}
        </ol>
      </div>
    </section>
  );
}
