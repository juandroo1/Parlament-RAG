import { useState } from "react";
import type { Source } from "../api";
import { snippet, sourceContext, sourceTitle } from "../format";

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
        "scroll-mt-6 rounded-lg border p-4 transition-colors duration-700 " +
        (highlighted
          ? "border-red-700 bg-red-50 dark:bg-red-950/40"
          : "border-slate-200 bg-white dark:border-slate-700 dark:bg-slate-900")
      }
    >
      <div className="flex gap-3">
        <span className="mt-0.5 h-fit rounded bg-slate-100 px-2 py-0.5 text-sm font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-200">
          [{source.number}]
        </span>
        <div className="min-w-0 flex-1">
          <p className="font-medium">{sourceTitle(source)}</p>
          <p className="text-sm text-slate-600 dark:text-slate-400">{sourceContext(source)}</p>
          <p className="mt-1 text-sm text-slate-500 dark:text-slate-400">{source.title}</p>
          <blockquote className="mt-3 border-l-2 border-slate-300 pl-3 text-sm text-slate-700 dark:border-slate-600 dark:text-slate-300">
            «{expanded ? source.text : short}»
          </blockquote>
          <div className="mt-3 flex flex-wrap gap-4 text-sm">
            {canExpand && (
              <button
                type="button"
                className="text-slate-600 hover:underline dark:text-slate-300"
                onClick={() => setExpanded((value) => !value)}
              >
                {expanded ? "Weniger zeigen" : "Ganzen Abschnitt zeigen"}
              </button>
            )}
            <a
              href={source.url}
              target="_blank"
              rel="noreferrer"
              className="font-medium text-red-800 hover:underline dark:text-red-300"
            >
              Originalstelle auf parlament.ch ↗
            </a>
          </div>
        </div>
      </div>
    </li>
  );
}
