import { describe, expect, it } from "vitest";
import type { Source, Usage } from "./api";
import { SPEECH } from "./test/fixtures";
import {
  formatDate,
  snippet,
  sourceContext,
  sourceTitle,
  splitCitations,
  usageLine,
} from "./format";
import { fr } from "./i18n/fr";

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
      /7\s818 tokens d'entrée et 310 de sortie/,
    );
    expect(usageLine({ ...usage, model: null }, fr)).toBe(
      "Aucun appel à l'IA · 6.0 s",
    );
  });
});
