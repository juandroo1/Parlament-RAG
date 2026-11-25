import { describe, expect, it } from "vitest";
import type { Source, Usage } from "./api";
import { SPEECH } from "./test/fixtures";
import {
  citationRuns,
  fold,
  formatDate,
  longDate,
  periodLabel,
  speakerLabel,
  snippet,
  sourceContext,
  sourceTitle,
  splitCitations,
  usageLine,
} from "./format";
import { fr } from "./i18n/fr";
import { SPEAKERS } from "./test/fixtures";

describe("splitCitations", () => {
  it("findet einzelne, gruppierte und aufeinanderfolgende Zitate", () => {
    expect(splitCitations("Erstens [2]. Zweitens [1, 3][4].")).toEqual([
      { kind: "text", text: "Erstens " },
      { kind: "cite", numbers: [2] },
      { kind: "text", text: ". Zweitens " },
      { kind: "cite", numbers: [1, 3] },
      { kind: "cite", numbers: [4] },
      { kind: "text", text: "." },
    ]);
  });

  it("lässt Text ohne Zitate unverändert", () => {
    expect(splitCitations("Kein Zitat [a].")).toEqual([
      { kind: "text", text: "Kein Zitat [a]." },
    ]);
  });
});

describe("Quellen", () => {
  it("zeigt Bundesratsmitglieder als Bundesrat", () => {
    expect(sourceTitle(SPEECH)).toBe("Rösti Albert (Bundesrat)");
    expect(sourceContext(SPEECH)).toBe("Nationalrat · 30.09.2026 · 26.9022");
  });

  it("zeigt Fraktion und Kanton bei Ratsmitgliedern", () => {
    const member = {
      ...SPEECH,
      speaker_name: "Michel Matthias",
      speaker_function: null,
      parl_group: "RL",
      canton: "ZG",
      council: "SR",
    };
    expect(sourceTitle(member)).toBe("Michel Matthias (RL, ZG)");
    expect(sourceContext(member)).toBe("Ständerat · 30.09.2026 · 26.9022");
  });

  it("zeigt Geschäfte mit Nummer und Abschnitt", () => {
    const business: Source = {
      ...SPEECH,
      source_type: "business",
      speaker_name: null,
      speaker_function: null,
      council: null,
      business_numbers: ["25.3906"],
      section: "Stellungnahme des Bundesrates",
      date: "2025-06-20",
    };
    expect(sourceTitle(business)).toBe(
      "Geschäft 25.3906 · Stellungnahme des Bundesrates",
    );
    expect(sourceContext(business)).toBe("eingereicht 20.06.2025");
  });

  it("kürzt lange Ausschnitte an einer Wortgrenze", () => {
    const short = snippet("Wort ".repeat(100), 30);
    expect(short.endsWith(" …")).toBe(true);
    expect(short.length).toBeLessThanOrEqual(32);
    expect(snippet("kurz\n\ntext")).toBe("kurz text");
  });
});

describe("usageLine", () => {
  const usage: Usage = {
    model: "claude-opus-5-5",
    backend: "api",
    input_tokens: 9100,
    output_tokens: 1300,
    cost_usd: 0.0622,
    cost_estimated: false,
    latency_ms: 6040,
  };

  it("zeigt Modell, Tokens, Kosten und Dauer", () => {
    const line = usageLine(usage);
    expect(line).toContain("claude-opus-5-5");
    expect(line).toContain("Output-Tokens");
    expect(line).toContain("0.0622 USD");
    expect(line).toContain("6.0 s");
  });

  it("kennzeichnet Abo-Kosten als Schätzung", () => {
    expect(usageLine({ ...usage, cost_estimated: true })).toContain(
      "geschätzt, im Claude-Abo enthalten",
    );
  });

  it("ohne KI-Aufruf", () => {
    expect(usageLine({ ...usage, model: null, latency_ms: 120 })).toBe(
      "Kein KI-Aufruf · 0.1 s",
    );
  });
});

describe("auf Französisch", () => {
  it("übersetzt Bundesrat, Rat und Geschäft", () => {
    expect(sourceTitle(SPEECH, fr)).toBe("Rösti Albert (Conseil fédéral)");
    expect(sourceContext(SPEECH, fr)).toBe(
      "Conseil national · 30.09.2026 · 26.9022",
    );
    const business: Source = {
      ...SPEECH,
      source_type: "business",
      speaker_name: null,
      council: null,
      business_numbers: ["25.3906"],
      section: "Avis du Conseil fédéral",
      date: "2025-06-20",
    };
    expect(sourceTitle(business, fr)).toBe(
      "Objet 25.3906 · Avis du Conseil fédéral",
    );
    expect(sourceContext(business, fr)).toBe("déposé le 20.06.2025");
  });

  it("formatiert Datum und Zahlen je Sprache", () => {
    expect(formatDate("2026-03-04", "fr-CH")).toBe("04.03.2026");
    const usage: Usage = {
      model: "claude-haiku-5-5",
      backend: "api",
      input_tokens: 7818,
      output_tokens: 310,
      cost_usd: 0.000937,
      cost_estimated: false,
      latency_ms: 6040,
    };
    expect(usageLine(usage)).toMatch(/7['’]818 Input- und 310 Output-Tokens/);
    expect(usageLine(usage, fr)).toMatch(
      // Je nach ICU-Daten «7 818» oder «7'818».
      /7[\s'’]818 tokens d’entrée et 310 de sortie/,
    );
    expect(usageLine({ ...usage, model: null }, fr)).toBe(
      "Aucun appel à l’IA · 6.0 s",
    );
  });
});

describe("citationRuns", () => {
  it("hängt Satzzeichen an das Zitat und schützt das Leerzeichen davor", () => {
    expect(
      citationRuns("Strom fehlt [7]. Wie die Reserve [7][8], so auch [2]"),
    ).toEqual([
      { kind: "text", text: "Strom fehlt " },
      { kind: "cite", numbers: [7], trail: "." },
      { kind: "text", text: " Wie die Reserve " },
      { kind: "cite", numbers: [7], trail: "" },
      { kind: "cite", numbers: [8], trail: "," },
      { kind: "text", text: " so auch " },
      { kind: "cite", numbers: [2], trail: "" },
    ]);
  });

  it("lässt Text ohne Zitate unverändert", () => {
    expect(citationRuns("Kein Zitat.")).toEqual([
      { kind: "text", text: "Kein Zitat." },
    ]);
  });
});

describe("Zeitraum und Personen (Spec 003)", () => {
  it("schreibt Zeiträume kurz", () => {
    expect(periodLabel("2025-01-01", "2025-12-31")).toBe("2025");
    expect(periodLabel("2025-03-01", "2025-03-31")).toBe("März 2025");
    expect(periodLabel("2025-03-01", "2025-03-31", fr)).toBe("mars 2025");
    expect(periodLabel("2024-02-01", "2024-02-29")).toBe("Februar 2024"); // Schaltjahr
    expect(periodLabel("2026-09-14", "2026-10-02")).toBe("14.09.2026–02.10.2026");
    expect(periodLabel("2025-01-01", null)).toBe("seit 01.01.2025");
    expect(periodLabel(null, "2024-12-31", fr)).toBe("jusqu’au 31.12.2024");
  });

  it("schreibt lange Daten je Sprache", () => {
    expect(longDate("2023-12-04")).toBe("4. Dezember 2023");
    expect(longDate("2026-10-02", "fr-CH")).toBe("2 octobre 2026");
  });

  it("beschriftet Personen", () => {
    const [aebischer, , , , roesti] = SPEAKERS;
    expect(speakerLabel(aebischer)).toBe("Aebischer Matthias (S, BE)");
    expect(speakerLabel(roesti)).toBe("Rösti Albert (Bundesrat)");
    expect(speakerLabel(roesti, fr)).toBe("Rösti Albert (Conseil fédéral)");
  });

  it("vergleicht ohne Akzente und Grossschreibung", () => {
    expect(fold("Rösti Céline")).toBe("rosti celine");
  });
});
