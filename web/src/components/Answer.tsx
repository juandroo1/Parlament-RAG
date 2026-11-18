import { useEffect, useRef, useState } from "react";
import type { AskResponse } from "../api";
import { splitCitations, usageLine } from "../format";
import { useI18n } from "../i18n/LanguageProvider";
import { SourceCard } from "./SourceCard";

export function Answer({ result }: { result: AskResponse }) {
  const { t } = useI18n();
  const [highlighted, setHighlighted] = useState<number | null>(null);
  const timer = useRef<number | undefined>(undefined);
  const numbers = new Set(result.sources.map((source) => source.number));

  useEffect(() => () => window.clearTimeout(timer.current), []);

  const jumpTo = (number: number) => {
    const element = document.getElementById(`quelle-${number}`);
    const smooth = !window.matchMedia?.("(prefers-reduced-motion: reduce)")
      .matches;
    element?.scrollIntoView?.({
      behavior: smooth ? "smooth" : "auto",
      block: "nearest",
    });
    element?.focus({ preventScroll: true });
    setHighlighted(number);
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => setHighlighted(null), 2000);
  };

  if (result.insufficient_context) {
    return (
      <section
        aria-live="polite"
        className="rounded-2xl border border-warn-border bg-warn-bg p-5"
      >
        <h2 className="font-display text-lg font-extrabold">
          {t.answer.insufficientTitle}
        </h2>
        <p className="mt-2">{result.answer}</p>
        {result.insufficient_reason &&
          t.answer.reasons[result.insufficient_reason] && (
            <p className="mt-2 text-sm text-muted">
              {t.answer.reasons[result.insufficient_reason]} {t.answer.tryAgain}
            </p>
          )}
        <p className="mt-3 text-xs text-muted">{usageLine(result.usage, t)}</p>
      </section>
    );
  }

  return (
    <section aria-live="polite" className="space-y-10">
      <div>
        <div className="flex flex-wrap items-center gap-2.5">
          <h2 className="font-display text-[22px] font-extrabold sm:text-2xl">
            {t.answer.title}
          </h2>
          <span className="rounded-full bg-surface-2 px-2.5 py-1 text-xs text-muted sm:text-[13px]">
            {t.answer.badge(result.sources.length)}
          </span>
        </div>
        <p className="mt-3 max-w-[62ch] text-[17px] leading-[1.75] whitespace-pre-line sm:mt-4 sm:text-lg">
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
                      aria-label={t.answer.citation(number)}
                      className="mx-0.5 inline-block min-w-6 rounded-md bg-cite-bg px-1.5 text-center align-[1px] text-[13px] leading-6 font-bold text-accent-text no-underline hover:underline"
                      onClick={(event) => {
                        event.preventDefault();
                        jumpTo(number);
                      }}
                    >
                      {number}
                    </a>
                  ) : (
                    <span
                      key={number}
                      className="mx-0.5 text-[13px] text-muted"
                    >
                      [{number}]
                    </span>
                  ),
                )}
              </span>
            ),
          )}
        </p>
        <p className="mt-3 text-xs text-muted">{usageLine(result.usage, t)}</p>
      </div>
      <div>
        <h2 className="font-display text-xl font-extrabold">
          {t.answer.sources}
        </h2>
        <ol className="mt-3.5 space-y-3">
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
