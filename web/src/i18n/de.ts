// Texte der Oberfläche auf Deutsch: Quelle aller Schlüssel (Spec 002, US-10). fr.ts muss denselben
// Typ erfüllen; ein fehlender Schlüssel ist ein Fehler bei `tsc` (AK-10.5).

export const de = {
  locale: "de-CH",
  pageTitle: "Frag das Parlament",
  pageDescription:
    "Fragen zu Debatten und Geschäften des Schweizer Bundesparlaments, mit überprüfbaren Quellen.",
  notice: "Privates Projekt – keine amtliche Veröffentlichung",
  languageLabel: "Sprache",
  theme: {
    label: "Darstellung",
    light: "Hell",
    dark: "Dunkel",
    system: "Wie System",
    current: (name: string) => `Darstellung: ${name}`,
  },
  hero: {
    title: "Was wurde im Parlament gesagt?",
    lead: "Stellen Sie eine Frage auf Deutsch oder Französisch. Die Antwort stützt sich auf das Amtliche Bulletin und Curia Vista, jede Aussage mit Quelle.",
  },
  form: {
    label: "Ihre Frage",
    hint: "(Deutsch oder Französisch)",
    placeholder: "z. B. Was sagte der Bundesrat zur Motion …?",
    examples: "Beispiele:",
    // Je eine Frage in der anderen Sprache zeigt die sprachübergreifende Suche.
    exampleQuestions: [
      {
        text: "Was sagte Bundesrat Rösti zum Kühlwasser der Kernkraftwerke während der Hitzewelle?",
        lang: "de",
      },
      {
        text: "Qu’a dit le Conseil fédéral sur la 13e rente AVS au Conseil des Etats ?",
        lang: "fr",
      },
      {
        text: "Weshalb lehnte der Bundesrat die Landschaftsinitiative ab?",
        lang: "de",
      },
    ],
    filter: "Filter",
    activeFilters: (count: number) => `${count} aktiv`,
    council: "Rat",
    allCouncils: "Alle Räte",
    group: "Fraktion",
    allGroups: "Alle Fraktionen",
    groupNote:
      "Mit Fraktionsfilter werden nur Voten durchsucht, keine Geschäftstexte.",
    from: "Von",
    to: "Bis",
    submit: "Fragen",
    searching: "Suche läuft …",
  },
  loading:
    "Quellen werden gesucht und die Antwort wird geschrieben. Das kann 5 bis 15 Sekunden dauern …",
  answer: {
    title: "Antwort",
    sources: "Quellen",
    badge: (count: number) =>
      count === 1
        ? "KI-Antwort aus 1 Quelle"
        : `KI-Antwort aus ${count} Quellen`,
    citation: (number: number) => `Quelle ${number}`,
    insufficientTitle: "Keine ausreichende Grundlage",
    reasons: {
      no_hits: "Die Suche fand keine passenden Abschnitte.",
      low_similarity: "Die gefundenen Abschnitte passen zu wenig zur Frage.",
      model: "Die gefundenen Abschnitte beantworten die Frage nicht.",
    } as Record<string, string>,
    tryAgain: "Versuchen Sie eine konkretere Frage oder andere Filter.",
  },
  source: {
    label: "Quelle",
    federalCouncil: "Bundesrat",
    unknown: "Unbekannt",
    business: "Geschäft",
    submitted: (date: string) => `eingereicht ${date}`,
    expand: "Ganzen Abschnitt zeigen",
    collapse: "Weniger zeigen",
    original: "Originalstelle auf parlament.ch",
  },
  usage: {
    noModel: "Kein KI-Aufruf",
    tokens: (input: string, output: string) =>
      `${input} Input- und ${output} Output-Tokens`,
    costUnknown: "Kosten unbekannt",
    costEstimated: (cost: string) =>
      `≈ ${cost} USD geschätzt, im Claude-Abo enthalten`,
  },
  councils: {
    NR: "Nationalrat",
    SR: "Ständerat",
    V: "Vereinigte Bundesversammlung",
  },
  // Fraktionen der 52. Legislatur; Kürzel wie in den Daten der Parlamentsdienste.
  parlGroups: {
    V: "SVP-Fraktion",
    S: "Sozialdemokratische Fraktion",
    "M-E": "Mitte-Fraktion",
    RL: "FDP-Liberale Fraktion",
    G: "Grüne Fraktion",
    GL: "Grünliberale Fraktion",
  },
  errors: {
    network: "Die API ist nicht erreichbar. Läuft der Server?",
    invalid: (fields: string) =>
      `Die Eingabe ist ungültig${fields ? `: ${fields}` : "."}`,
    http: (status: number) =>
      `Die Anfrage ist fehlgeschlagen (HTTP ${status}).`,
    unexpected: "Unerwarteter Fehler. Bitte erneut versuchen.",
  },
  footer: {
    sourceLabel: "Quelle:",
    sourceBefore:
      "Parlamentsdienste der Bundesversammlung, Bern. Open Data über den Webservice",
    sourceAfter:
      "(Amtliches Bulletin und Curia Vista), Sessionen bis 2. Oktober 2026, heruntergeladen am 12. und 13. November 2026.",
    notOfficialLabel: "Keine amtliche Veröffentlichung:",
    notOfficial:
      "ein privates Projekt, nicht von den Parlamentsdiensten. Die Antworten erzeugt ein KI-Modell aus den gefundenen Abschnitten. Massgebend sind die verlinkten Originalstellen auf parlament.ch. Das System gibt wieder, was gesagt wurde, und bewertet keine Personen, Parteien oder Vorlagen.",
    demo: "Die öffentliche Demo hat ein begrenztes Tagesbudget und eine Grenze von Fragen pro Stunde.",
    codeBefore: "Code unter",
    license: "MIT-Lizenz",
    codeAfter: ".",
  },
};

export type Messages = typeof de;
