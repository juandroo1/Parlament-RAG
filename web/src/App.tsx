import { useState } from "react";
import { ApiError, ask, buildRequest, type AskResponse, type Filters } from "./api";
import { Answer } from "./components/Answer";
import { AskForm } from "./components/AskForm";

type State =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "done"; result: AskResponse }
  | { status: "error"; message: string };

export default function App() {
  const [state, setState] = useState<State>({ status: "idle" });

  const submit = async (question: string, filters: Filters) => {
    setState({ status: "loading" });
    try {
      const result = await ask(buildRequest(question, filters));
      setState({ status: "done", result });
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : "Unerwarteter Fehler. Bitte erneut versuchen.";
      setState({ status: "error", message });
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 dark:bg-slate-950 dark:text-slate-100">
      <main className="mx-auto max-w-3xl px-4 py-8 sm:py-12">
        <header className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight">Frag das Parlament</h1>
          <p className="mt-2 text-slate-600 dark:text-slate-400">
            Fragen zu Debatten und Geschäften des Schweizer Bundesparlaments, beantwortet aus dem
            Amtlichen Bulletin und Curia Vista. Jede Aussage verweist auf ihre Quelle.
          </p>
        </header>

        <AskForm loading={state.status === "loading"} onSubmit={submit} />

        <div className="mt-8">
          {state.status === "loading" && (
            <p role="status" className="animate-pulse text-slate-600 dark:text-slate-400">
              Quellen werden gesucht und die Antwort wird geschrieben. Das kann 5 bis 15 Sekunden
              dauern …
            </p>
          )}
          {state.status === "error" && (
            <div
              role="alert"
              className="rounded-lg border border-red-300 bg-red-50 p-4 text-red-900 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200"
            >
              {state.message}
            </div>
          )}
          {state.status === "done" && <Answer result={state.result} />}
        </div>
      </main>

      <footer className="border-t border-slate-200 dark:border-slate-800">
        <div className="mx-auto max-w-3xl space-y-2 px-4 py-6 text-sm text-slate-600 dark:text-slate-400">
          <p>
            <strong>Datenquelle:</strong> Open Data der Parlamentsdienste der Bundesversammlung über
            den OData-Dienst{" "}
            <a className="underline" href="https://ws.parlament.ch/odata.svc/" target="_blank" rel="noreferrer">
              ws.parlament.ch
            </a>{" "}
            (Amtliches Bulletin und Curia Vista), Stand 2. Oktober 2026.
          </p>
          <p>
            Die Antworten erzeugt ein KI-Modell aus den gefundenen Abschnitten. Massgebend sind die
            verlinkten Originalstellen auf parlament.ch. Das System gibt wieder, was gesagt wurde,
            und bewertet keine Personen, Parteien oder Vorlagen.
          </p>
          <p>
            Code unter{" "}
            <a
              className="underline"
              href="https://github.com/juandroo1/Parlament-RAG/blob/main/LICENSE"
              target="_blank"
              rel="noreferrer"
            >
              MIT-Lizenz
            </a>
            .
          </p>
        </div>
      </footer>
    </div>
  );
}
