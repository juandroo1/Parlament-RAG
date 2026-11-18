import { useState } from "react";
import type { Source } from "../api";
import { snippet, sourceContext, sourceTitle } from "../format";
import { ExternalIcon } from "./icons";

interface Props {
  source: Source;
  highlighted: boolean;
}

export function SourceCard({ source, highlighted }: Props) {
  const [expanded, setExpanded] = useState(false);
  const short = snippet(source.text);
  const canExpand = short !== source.text.split(/\s+/).join(" ").trim();

  return (
    <li
      id={`quelle-${source.number}`}
      tabIndex={-1}
      className={
        "scroll-mt-6 rounded-2xl border p-4 transition-colors duration-700 motion-reduce:transition-none sm:p-[18px] " +
        (highlighted ? "border-accent bg-cite-bg" : "border-border bg-surface")
      }
    >
      <div className="flex gap-3 sm:gap-3.5">
        <span className="flex size-[30px] shrink-0 items-center justify-center rounded-lg bg-cite-bg text-sm font-bold text-accent-text">
          <span className="sr-only">Quelle </span>
          {source.number}
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-semibold">{sourceTitle(source)}</p>
          <p className="mt-0.5 text-sm text-muted">{sourceContext(source)}</p>
          <p className="mt-0.5 text-sm text-muted">{source.title}</p>
          <blockquote className="mt-2.5 text-[15px] leading-relaxed italic">
            «{expanded ? source.text : short}»
          </blockquote>
          <div className="mt-1.5 flex flex-wrap gap-x-5 text-sm">
            {canExpand && (
              <button
                type="button"
                className="min-h-11 font-semibold text-muted hover:underline sm:min-h-8"
                onClick={() => setExpanded((value) => !value)}
              >
                {expanded ? "Weniger zeigen" : "Ganzen Abschnitt zeigen"}
              </button>
            )}
            <a
              href={source.url}
              target="_blank"
              rel="noreferrer"
              className="inline-flex min-h-11 items-center gap-1.5 font-semibold text-accent-text hover:underline sm:min-h-8"
            >
              Originalstelle auf parlament.ch
              <ExternalIcon />
            </a>
          </div>
        </div>
      </div>
    </li>
  );
}
