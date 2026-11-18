import { useEffect, useId, useRef } from "react";
import { useI18n } from "../i18n/LanguageProvider";
import { CloseIcon, InfoIcon } from "./icons";

const REPO = "https://github.com/juandroo1/Parlament-RAG";

/**
 * Knopf und Dialog «So funktioniert's» (Spec 002, US-12). Natives <dialog> mit showModal():
 * Fokusfalle, Esc und Sperre des Hintergrunds kommen vom Browser. Beim Schliessen geht der Fokus
 * ausdrücklich an den Knopf zurück (AK-12.2).
 */
export function HowItWorks() {
  const { t } = useI18n();
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  const titleId = useId();

  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    const onClose = () => trigger.current?.focus();
    element.addEventListener("close", onClose);
    return () => element.removeEventListener("close", onClose);
  }, []);

  const close = () => dialog.current?.close();

  return (
    <>
      <button
        ref={trigger}
        type="button"
        aria-haspopup="dialog"
        aria-label={t.howItWorks.button}
        title={t.howItWorks.button}
        onClick={() => dialog.current?.showModal()}
        className="flex size-11 items-center justify-center gap-2 rounded-full border border-border text-text hover:border-primary sm:h-11 sm:w-auto sm:px-3.5 sm:text-sm sm:font-semibold"
      >
        <InfoIcon />
        <span className="hidden sm:inline">{t.howItWorks.button}</span>
      </button>

      <dialog
        ref={dialog}
        aria-labelledby={titleId}
        // Klick auf den abgedunkelten Hintergrund schliesst (das Ziel ist dann das <dialog> selbst).
        onClick={(event) => {
          if (event.target === event.currentTarget) close();
        }}
        className="m-0 mt-auto max-h-[85dvh] w-full max-w-none rounded-t-2xl border-t border-border bg-bg p-0 text-text shadow-card backdrop:bg-overlay motion-safe:animate-sheet-in sm:mt-0 sm:ml-auto sm:h-dvh sm:max-h-none sm:w-[440px] sm:rounded-none sm:rounded-l-2xl sm:border-t-0 sm:border-l sm:motion-safe:animate-panel-in"
      >
        <div className="flex min-h-full flex-col px-5 pt-2.5 pb-7 sm:px-7 sm:pt-6">
          <div
            aria-hidden="true"
            className="mx-auto mb-2 h-1 w-10 rounded-full bg-border sm:hidden"
          />
          <div className="flex items-center justify-between gap-3">
            <h2
              id={titleId}
              className="font-display text-xl font-extrabold sm:text-[22px]"
            >
              {t.howItWorks.title}
            </h2>
            <button
              type="button"
              aria-label={t.howItWorks.close}
              title={t.howItWorks.close}
              onClick={close}
              className="flex size-11 shrink-0 items-center justify-center rounded-full border border-border hover:border-primary"
            >
              <CloseIcon />
            </button>
          </div>
          <div className="mt-3 space-y-5">
            {t.howItWorks.sections.map((section) => (
              <section key={section.title}>
                <h3 className="font-semibold">{section.title}</h3>
                <p className="mt-1 text-[15px] leading-relaxed text-muted">
                  {section.text}
                </p>
              </section>
            ))}
          </div>
          <div className="mt-7 flex flex-col gap-2 sm:flex-row sm:flex-wrap">
            <a
              href={REPO}
              target="_blank"
              rel="noreferrer"
              className="inline-flex min-h-12 items-center justify-center rounded-xl bg-primary px-4 font-bold text-on-primary hover:opacity-90 sm:min-h-11"
            >
              {t.howItWorks.linkCode}
            </a>
            <a
              href={`${REPO}#ergebnisse`}
              target="_blank"
              rel="noreferrer"
              className="inline-flex min-h-12 items-center justify-center rounded-xl border border-border px-4 font-bold hover:border-primary sm:min-h-11"
            >
              {t.howItWorks.linkEvals}
            </a>
          </div>
        </div>
      </dialog>
    </>
  );
}
