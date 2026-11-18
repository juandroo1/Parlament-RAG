/** Quelle, Stand, Hinweis «keine amtliche Veröffentlichung» und Lizenz (AK-8.4, Task 6.3a). */
export function Footer() {
  const link = "font-semibold text-text underline underline-offset-2";
  return (
    <footer className="border-t border-border bg-surface">
      <div className="mx-auto max-w-[1120px] space-y-2 px-4 pt-6 pb-8 text-[13px] leading-relaxed text-muted sm:px-6 sm:pt-7 sm:pb-9">
        <p>
          <strong className="font-semibold text-text">Quelle:</strong>{" "}
          Parlamentsdienste der Bundesversammlung, Bern. Open Data über den
          Webservice{" "}
          <a
            className={link}
            href="https://ws.parlament.ch/odata.svc/"
            target="_blank"
            rel="noreferrer"
          >
            ws.parlament.ch
          </a>{" "}
          (Amtliches Bulletin und Curia Vista), Sessionen bis 2. Oktober 2026,
          heruntergeladen am 12. und 13. November 2026.
        </p>
        <p>
          <strong className="font-semibold text-text">
            Keine amtliche Veröffentlichung:
          </strong>{" "}
          ein privates Projekt, nicht von den Parlamentsdiensten. Die Antworten
          erzeugt ein KI-Modell aus den gefundenen Abschnitten. Massgebend sind
          die verlinkten Originalstellen auf parlament.ch. Das System gibt
          wieder, was gesagt wurde, und bewertet keine Personen, Parteien oder
          Vorlagen.
        </p>
        <p>
          Die öffentliche Demo hat ein begrenztes Tagesbudget und eine Grenze
          von Fragen pro Stunde.
        </p>
        <p>
          Code unter{" "}
          <a
            className={link}
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
  );
}
