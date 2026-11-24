# Eval-Lauf 2026-11-24 12:34 · full (person-zeit) · vector · haiku-low

- Commit: `5db9a91`
- Goldset: `evals/datasets/golden.jsonl`, 17 Fragen, davon 11 gemessen (6 unbeantwortbare übersprungen)
- Vergleich: Teillauf derselben Baseline vor dem Taggen von q29 und q62 (Commit `2605d57`, 15 Fragen, nicht aufbewahrt); die Antworten wurden per `--resume` übernommen, neu liefen nur q29 und q62
- Konfiguration: `chunks_per_query=100`, `retrieval_candidates=50`, `retrieval_rrf_k=60`, `embedding_model=BAAI/bge-m3`, `embedding_max_seq_length=1024`, `index_signature=BAAI/bge-m3|target=500|overlap=0.15|header=1|chunker=v1`, `database=parlrag`, `answer_min_similarity=0.55`, `retrieval_rerank=False`
- Korpus: 42'515 Dokumente, 102'891 Chunks

> Der Vorlauf hat andere Fragen gemessen; die Differenzen sind nur bedingt vergleichbar.

## Metriken

| Metrik | Wert | Vorlauf | Δ |
|---|---|---|---|
| Recall@5 | 0.591 | 0.591 | ±0.000 |
| Recall@10 | 0.750 | 0.750 | ±0.000 |
| Recall@20 | 0.841 | 0.841 | ±0.000 |
| MRR@10 | 0.617 | 0.617 | ±0.000 |
| Suchdauer p50 | 151 ms | 170 ms | -19 ms |
| Suchdauer p95 | 192 ms | 199 ms | -7 ms |
| Zitiergenauigkeit | 0.967 | 0.967 | ±0.000 |
| Faithfulness | 0.990 | 0.990 | ±0.000 |
| Ablehnungsquote (unbeantwortbar) | 1.000 | 1.000 | ±0.000 |
| Ausserhalb erkannt, ohne LLM | 0.000 | 0.000 | ±0.000 |
| Falsche Ablehnungen | 0.091 | 0.091 | ±0.000 |
| Antwortsprache | 1.000 | 1.000 | ±0.000 |
| Antwortzeit p50 | 6169 ms | 6535 ms | -366 ms |
| Antwortzeit p95 | 13053 ms | 13053 ms | +0 ms |
| Kosten Antwort pro Frage | 0.0021 USD | 0.0021 USD | -0.0000 USD |
| Kosten Judge pro Frage | 0.0397 USD | 0.0397 USD | +0.0000 USD |

## Teilsets

| Teilset | n | Recall@5 | Recall@10 | Recall@20 | MRR@10 | Δ Recall@10 |
|---|---|---|---|---|---|---|
| de | 7 | 0.786 | 0.821 | 0.893 | 0.786 | ±0.000 |
| fr | 4 | 0.250 | 0.625 | 0.750 | 0.323 | ±0.000 |
| crosslingual | 2 | 0.000 | 0.500 | 0.500 | 0.083 | ±0.000 |
| person-zeit | 11 | 0.591 | 0.750 | 0.841 | 0.617 | ±0.000 |

## Schwelle für «keine ausreichende Grundlage»

Schwelle 0.55: fängt 0 von 6 unbeantwortbaren Fragen ohne LLM ab, weist 0 von 11 beantwortbaren fälschlich ab.

| Schwelle | unbeantwortbar abgefangen | beantwortbar fälschlich abgewiesen |
|---|---|---|
| 0.50 | 0 / 6 | 0 / 11 |
| 0.51 | 0 / 6 | 0 / 11 |
| 0.52 | 0 / 6 | 0 / 11 |
| 0.53 | 0 / 6 | 0 / 11 |
| 0.54 | 0 / 6 | 0 / 11 |
| 0.55 (aktuell) | 0 / 6 | 0 / 11 |
| 0.56 | 0 / 6 | 0 / 11 |
| 0.57 | 0 / 6 | 1 / 11 |
| 0.58 | 0 / 6 | 1 / 11 |
| 0.59 | 0 / 6 | 1 / 11 |
| 0.60 | 1 / 6 | 1 / 11 |
| 0.61 | 2 / 6 | 1 / 11 |
| 0.62 | 2 / 6 | 1 / 11 |
| 0.63 | 2 / 6 | 2 / 11 |
| 0.64 | 2 / 6 | 2 / 11 |
| 0.65 | 4 / 6 | 3 / 11 |

## Antworten

17 Fragen: 10 beantwortet, 7 abgelehnt, 0 Fehler; 10 vom Judge bewertet. Antworten: claude-haiku-5-5 (`low`), Judge: claude-sonnet-5-5 (`medium`), Backend `claude-code`. Über das Claude-Abo: Antwortzeiten enthalten den Start der CLI, Kosten sind Schätzungen von Claude Code.

| Frage | Art | Ergebnis | erwartete zitiert | Zitiergenauigkeit | Faithfulness | Sprache | neutral | Zeit |
|---|---|---|---|---|---|---|---|---|
| q29 | unbeantwortbar | abgelehnt (Modell) | - | - | - | ja | - | 3688 ms |
| q62 | unbeantwortbar | abgelehnt (Modell) | - | - | - | ja | - | 3363 ms |
| q66 | de | beantwortet | 2 | 1.000 | 1.000 | ja | - | 13053 ms |
| q67 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 4820 ms |
| q68 | fr | abgelehnt (Modell) | - | - | - | ja | - | 5575 ms |
| q69 | de | beantwortet | 2 | 1.000 | 1.000 | ja | - | 8292 ms |
| q70 | de | beantwortet | 0 | 1.000 | 1.000 | ja | - | 6535 ms |
| q71 | fr | beantwortet | 0 | 0.750 | 0.900 | ja | - | 8141 ms |
| q72 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 10594 ms |
| q73 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 6169 ms |
| q74 | de | beantwortet | 2 | 0.923 | 1.000 | ja | - | 10176 ms |
| q75 | fr | beantwortet | 2 | 1.000 | 1.000 | ja | - | 6870 ms |
| q76 | fr | beantwortet | 1 | 1.000 | 1.000 | ja | - | 10168 ms |
| q77 | unbeantwortbar | abgelehnt (Modell) | - | - | - | ja | - | 3086 ms |
| q78 | unbeantwortbar | abgelehnt (Modell) | - | - | - | ja | - | 3428 ms |
| q79 | unbeantwortbar | abgelehnt (Modell) | - | - | - | ja | - | 3477 ms |
| q80 | unbeantwortbar | abgelehnt (Modell) | - | - | - | ja | - | 3050 ms |

## Verfehlte Quellen (Recall@10 < 1)

- q68 (Recall@10 0.50): transcript:353634 #17, transcript:353642 #8
- q69 (Recall@10 0.75): transcript:356618 #10, transcript:356905 #35, transcript:374646 #2, transcript:376786 #1
- q70 (Recall@10 0.00): transcript:338625 #13, transcript:339318 nicht gefunden
- q71 (Recall@10 0.00): transcript:358497 nicht gefunden
