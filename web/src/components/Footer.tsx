import { useI18n } from "../i18n/LanguageProvider";

/** Quelle, Stand, Hinweis «keine amtliche Veröffentlichung» und Lizenz (AK-8.4, Task 6.3a). */
export function Footer() {
  const { t } = useI18n();
  const link = "font-semibold text-text underline underline-offset-2";
  return (
    <footer className="border-t border-border bg-surface">
      <div className="mx-auto max-w-[1120px] space-y-2 px-4 pt-6 pb-8 text-[13px] leading-relaxed text-muted sm:px-6 sm:pt-7 sm:pb-9">
        <p>
          <strong className="font-semibold text-text">
            {t.footer.sourceLabel}
          </strong>{" "}
          {t.footer.sourceBefore}{" "}
          <a
            className={link}
            href="https://ws.parlament.ch/odata.svc/"
            target="_blank"
            rel="noreferrer"
          >
            ws.parlament.ch
          </a>{" "}
          {t.footer.sourceAfter}
        </p>
        <p>
          <strong className="font-semibold text-text">
            {t.footer.notOfficialLabel}
          </strong>{" "}
          {t.footer.notOfficial}
        </p>
        <p>{t.footer.demo}</p>
        <p>
          {t.footer.codeBefore}{" "}
          <a
            className={link}
            href="https://github.com/juandroo1/Parlament-RAG/blob/main/LICENSE"
            target="_blank"
            rel="noreferrer"
          >
            {t.footer.license}
          </a>
          {t.footer.codeAfter}
        </p>
      </div>
    </footer>
  );
}
