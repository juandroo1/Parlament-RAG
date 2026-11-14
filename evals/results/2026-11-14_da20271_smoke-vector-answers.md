# Eval-Lauf 2026-11-14 15:45 · smoke · vector

- Commit: `da20271`
- Goldset: `evals/datasets/golden.jsonl`, 15 Fragen, davon 13 gemessen (2 unbeantwortbare übersprungen)
- Vergleich: `2026-11-14_15a2215_smoke-vector-answers.json` (Commit `15a2215`)
- Konfiguration: `chunks_per_query=100`, `retrieval_candidates=50`, `retrieval_rrf_k=60`, `embedding_model=BAAI/bge-m3`, `embedding_max_seq_length=1024`, `index_signature=BAAI/bge-m3|target=500|overlap=0.15|header=1|chunker=v1`, `answer_min_similarity=0.55`
- Korpus: 42'515 Dokumente, 102'891 Chunks

## Metriken

| Metrik | Wert | Vorlauf | Δ |
|---|---|---|---|
| Recall@5 | 0.577 | 0.577 | ±0.000 |
| Recall@10 | 0.731 | 0.731 | ±0.000 |
| Recall@20 | 0.910 | 0.910 | ±0.000 |
| MRR@10 | 0.389 | 0.389 | ±0.000 |
| Suchdauer p50 | 375 ms | 328 ms | +47 ms |
| Suchdauer p95 | 681 ms | 726 ms | -45 ms |
| Zitiergenauigkeit | 0.985 | 0.985 | ±0.000 |
| Faithfulness | 0.997 | 0.980 | +0.016 |
| Ablehnungsquote (unbeantwortbar) | 1.000 | 1.000 | ±0.000 |
| Falsche Ablehnungen | 0.000 | 0.000 | ±0.000 |
| Neutralität (wertend) | 1.000 | 1.000 | ±0.000 |
| Antwortsprache | 1.000 | 0.933 | +0.067 |
| Antwortzeit p50 | 8213 ms | 7498 ms | +715 ms |
| Antwortzeit p95 | 12640 ms | 12609 ms | +32 ms |
| Kosten Antwort pro Frage | 0.0021 USD | 0.0018 USD | +0.0003 USD |
| Kosten Judge pro Frage | 0.0379 USD | 0.0392 USD | -0.0013 USD |

## Teilsets

| Teilset | n | Recall@5 | Recall@10 | Recall@20 | MRR@10 | Δ Recall@10 |
|---|---|---|---|---|---|---|
| de | 10 | 0.617 | 0.750 | 0.883 | 0.386 | ±0.000 |
| fr | 3 | 0.444 | 0.667 | 1.000 | 0.400 | ±0.000 |
| crosslingual | 4 | 0.250 | 0.500 | 0.875 | 0.081 | ±0.000 |
| filter | 2 | 1.000 | 1.000 | 1.000 | 1.000 | ±0.000 |
| teilkorpus | 10 | 0.450 | 0.650 | 0.883 | 0.366 | ±0.000 |
| wertend | 2 | 0.167 | 0.500 | 0.667 | 0.100 | ±0.000 |

## Schwelle für «keine ausreichende Grundlage»

Schwelle 0.55: fängt 0 von 2 unbeantwortbaren Fragen ohne LLM ab, weist 0 von 13 beantwortbaren fälschlich ab.

| Schwelle | unbeantwortbar abgefangen | beantwortbar fälschlich abgewiesen |
|---|---|---|
| 0.50 | 0 / 2 | 0 / 13 |
| 0.51 | 0 / 2 | 0 / 13 |
| 0.52 | 0 / 2 | 0 / 13 |
| 0.53 | 0 / 2 | 0 / 13 |
| 0.54 | 0 / 2 | 0 / 13 |
| 0.55 (aktuell) | 0 / 2 | 0 / 13 |
| 0.56 | 0 / 2 | 0 / 13 |
| 0.57 | 0 / 2 | 0 / 13 |
| 0.58 | 0 / 2 | 0 / 13 |
| 0.59 | 0 / 2 | 2 / 13 |
| 0.60 | 0 / 2 | 2 / 13 |
| 0.61 | 0 / 2 | 2 / 13 |
| 0.62 | 0 / 2 | 2 / 13 |
| 0.63 | 0 / 2 | 2 / 13 |
| 0.64 | 0 / 2 | 2 / 13 |
| 0.65 | 1 / 2 | 2 / 13 |

## Antworten

15 Fragen: 13 beantwortet, 2 abgelehnt, 0 Fehler; 13 vom Judge bewertet. Antworten: claude-haiku-5-5 (`low`), Judge: claude-sonnet-5-5 (`medium`), Backend `claude-code`. Über das Claude-Abo: Antwortzeiten enthalten den Start der CLI, Kosten sind Schätzungen von Claude Code.

| Frage | Art | Ergebnis | erwartete zitiert | Zitiergenauigkeit | Faithfulness | Sprache | neutral | Zeit |
|---|---|---|---|---|---|---|---|---|
| q01 | de | beantwortet | 3 | 1.000 | 1.000 | ja | - | 4222 ms |
| q02 | de | beantwortet | 0 | 1.000 | 1.000 | ja | - | 10287 ms |
| q04 | fr | beantwortet | 0 | 1.000 | 1.000 | ja | - | 8213 ms |
| q05 | de | beantwortet | 3 | 0.889 | 1.000 | ja | - | 9846 ms |
| q07 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 3936 ms |
| q09 | de | beantwortet | 2 | 1.000 | 1.000 | ja | - | 7166 ms |
| q12 | fr | beantwortet | 1 | 1.000 | 1.000 | ja | - | 10261 ms |
| q13 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 6840 ms |
| q17 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 3365 ms |
| q18 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 10734 ms |
| q19 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 9410 ms |
| q26 | wertend | beantwortet | 0 | 0.917 | 0.958 | ja | ja | 12640 ms |
| q28 | wertend | beantwortet | 1 | 1.000 | 1.000 | ja | ja | 8885 ms |
| q29 | unbeantwortbar | abgelehnt (Modell) | - | - | - | ja | - | 3327 ms |
| q32 | unbeantwortbar | abgelehnt (Modell) | - | - | - | ja | - | 3254 ms |

## Verfehlte Quellen (Recall@10 < 1)

- q02 (Recall@10 0.00): transcript:422494 #20, transcript:422531 nicht gefunden
- q04 (Recall@10 0.00): transcript:422506 #11
- q07 (Recall@10 0.50): transcript:418909 #2, business:20244494 #15
- q26 (Recall@10 0.00): transcript:421345 nicht gefunden, transcript:421772 #11, transcript:421630 nicht gefunden
