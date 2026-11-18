import { useState } from "react";
import { ask, buildRequest, type AskResponse, type Filters } from "./api";
import { Answer } from "./components/Answer";
import { AskForm } from "./components/AskForm";
import { Footer } from "./components/Footer";
import { Header } from "./components/Header";
import { errorText } from "./i18n/errors";
import { LanguageProvider, useI18n } from "./i18n/LanguageProvider";

type State =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "done"; result: AskResponse }
  | { status: "error"; error: unknown };

export default function App() {
  return (
    <LanguageProvider>
      <Page />
    </LanguageProvider>
  );
}

function Page() {
  const { t } = useI18n();
  const [state, setState] = useState<State>({ status: "idle" });

  const submit = async (question: string, filters: Filters) => {
    setState({ status: "loading" });
    try {
      const result = await ask(buildRequest(question, filters));
      setState({ status: "done", result });
    } catch (error) {
      // Die Meldung entsteht erst beim Anzeigen, damit sie beim Sprachwechsel mitwechselt.
      setState({ status: "error", error });
    }
  };

  return (
    <div id="top" className="flex min-h-screen flex-col bg-bg text-text">
      <Header />

      <main className="mx-auto w-full max-w-[760px] flex-1 px-4 pb-16 sm:px-6">
        <section
          aria-labelledby="titel"
          className="pt-5 sm:pt-9 sm:text-center"
        >
          <h1
            id="titel"
            className="font-display text-[28px] leading-[1.15] font-extrabold tracking-tight sm:text-[42px]"
          >
            {t.hero.title}
          </h1>
          <p className="mt-2 text-[15px] leading-relaxed text-muted sm:mx-auto sm:mt-3.5 sm:max-w-[600px] sm:text-[17px]">
            {t.hero.lead}
          </p>
        </section>

        <AskForm loading={state.status === "loading"} onSubmit={submit} />

        <div className="mt-10 sm:mt-12">
          {state.status === "loading" && (
            <p role="status" className="text-muted motion-safe:animate-pulse">
              {t.loading}
            </p>
          )}
          {state.status === "error" && (
            <div
              role="alert"
              className="rounded-xl border border-error-border bg-error-bg p-4 text-error-text"
            >
              {errorText(state.error, t)}
            </div>
          )}
          {state.status === "done" && <Answer result={state.result} />}
        </div>
      </main>

      <Footer />
    </div>
  );
}
