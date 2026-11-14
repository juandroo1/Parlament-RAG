# Prüfung des Judge – Baseline-Lauf `2026-11-14_a201a9c_full-vector-answers`

Stichprobe: 7 von 65 Antworten (≈ 10 %), ausgewählt nach dem Grundsatz «auffällige zuerst»: die drei Antworten mit den meisten Urteilen `partial`, `unsupported` oder «stützt nicht», ergänzt durch DE, FR und eine wertende Frage. Zusammen 51 Urteile des Judge (Claude Sonnet 5.5, Effort `medium`) zu Antworten von Claude Haiku 5.5.

**Vorgehen:** Claude (Opus 5.5) hat jedes Urteil gegen den Wortlaut der zitierten Quellen geprüft und einen Vorschlag gemacht; Sandro hat den Vorschlag gesamthaft freigegeben, ohne jedes Urteil einzeln nachzuprüfen. Das ist eine Vorprüfung durch ein zweites Modell, keine unabhängige Prüfung von Hand im Sinn von plan.md, Abschnitt 9.

**Ergebnis:** 47 von 51 Urteilen bestätigt, **Übereinstimmung 92 %**.

| Antwort | Urteile | bestätigt | Abweichungen |
|---|---|---|---|
| q01 (DE) | 5 | 4 | Nr. 5 |
| q02 (DE, sprachübergreifend) | 7 | 6 | Nr. 1 |
| q04 (FR, sprachübergreifend) | 6 | 6 | – |
| q12 (FR) | 8 | 8 | – |
| q16 (FR) | 8 | 7 | Nr. 1 |
| q22 (DE) | 8 | 7 | Nr. 2 |
| q26 (DE, wertend, inkl. Neutralität) | 9 | 9 | – |

**Abweichungen:**

| Urteil | Judge | Vorschlag | Begründung |
|---|---|---|---|
| q01 Nr. 5 | `supported` | nicht einverstanden | Der Satz benennt nur eine Lücke («dieser Teil der Frage bleibt offen»); laut Judge-Prompt ist das keine Aussage und hätte nicht bewertet werden dürfen. Folge für die Metrik gering (gestützt). |
| q02 Nr. 1 | `supported` (ohne Quelle) | nicht einverstanden | «In der Debatte wurden die Schäden nicht beziffert»: Eine solche Verneinung können die übergebenen Quellen nicht belegen; tatsächlich nennt ein nicht übergebenes Votum (Suisse Grêle, 60 Mio. Franken) eine Zahl. Richtig wäre `unsupported` oder `partial`. Judge zu nachsichtig. |
| q16 Nr. 1 | `partial` | nicht einverstanden | «Die Motion 22.3477 umfasst drei Punkte»: Quelle [1] belegt die Einreichung im Mai 2022, Quelle [3] die drei Punkte; über alle Quellen ist die Aussage gestützt. Judge zu streng. |
| q22 Nr. 2 | `supported` | nicht einverstanden | «Ein Ziel ist, dass … über 20 Jahre verstreichen» verdreht den Sinn: Die lange Verfahrensdauer ist das Problem, nicht das Ziel. Richtig wäre `partial`. Judge zu nachsichtig. |

**Einordnung:** Die Urteile pro zitierter Quelle («stützt» / «stützt nicht») waren in allen 51 Fällen nachvollziehbar, auch die Fälle, in denen der Judge eine von zwei zitierten Quellen zu Recht als nicht stützend markiert (q12, q22, q26). Abweichungen betreffen die Gesamtstützung: zweimal zu nachsichtig bei einer Sinnverschiebung bzw. einer nicht belegbaren Verneinung, einmal zu streng, einmal eine Regel des Prompts nicht befolgt. Zitiergenauigkeit und Faithfulness des Laufs sind deshalb eher leicht überschätzt.
