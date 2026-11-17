# Eval-Lauf 2026-11-17 15:48 · smoke · vector · opus-high

- Commit: `6af0512`
- Goldset: `evals/datasets/golden.jsonl`, 15 Fragen, davon 13 gemessen (2 unbeantwortbare übersprungen)
- Vergleich: kein Vorlauf mit derselben Suite und demselben Modus
- Konfiguration: `chunks_per_query=100`, `retrieval_candidates=50`, `retrieval_rrf_k=60`, `embedding_model=BAAI/bge-m3`, `embedding_max_seq_length=1024`, `index_signature=BAAI/bge-m3|target=500|overlap=0.15|header=1|chunker=v1`, `database=parlrag`, `answer_min_similarity=0.55`, `retrieval_rerank=False`
- Korpus: 42'515 Dokumente, 102'891 Chunks

## Metriken

| Metrik | Wert | Vorlauf | Δ |
|---|---|---|---|
| Recall@5 | 0.577 | - | - |
| Recall@10 | 0.731 | - | - |
| Recall@20 | 0.910 | - | - |
| MRR@10 | 0.389 | - | - |
| Suchdauer p50 | 154 ms | - | - |
| Suchdauer p95 | 211 ms | - | - |
| Zitiergenauigkeit | 0.983 | - | - |
| Faithfulness | 1.000 | - | - |
| Ablehnungsquote (unbeantwortbar) | 1.000 | - | - |
| Falsche Ablehnungen | 0.000 | - | - |
| Neutralität (wertend) | 1.000 | - | - |
| Antwortsprache | 1.000 | - | - |
| Antwortzeit p50 | 10539 ms | - | - |
| Antwortzeit p95 | 19664 ms | - | - |
| Kosten Antwort pro Frage | 0.0252 USD | - | - |
| Kosten Judge pro Frage | 0.0444 USD | - | - |

## Teilsets

| Teilset | n | Recall@5 | Recall@10 | Recall@20 | MRR@10 | Δ Recall@10 |
|---|---|---|---|---|---|---|
| de | 10 | 0.617 | 0.750 | 0.883 | 0.386 | - |
| fr | 3 | 0.444 | 0.667 | 1.000 | 0.400 | - |
| crosslingual | 4 | 0.250 | 0.500 | 0.875 | 0.081 | - |
| filter | 2 | 1.000 | 1.000 | 1.000 | 1.000 | - |
| teilkorpus | 10 | 0.450 | 0.650 | 0.883 | 0.366 | - |
| wertend | 2 | 0.167 | 0.500 | 0.667 | 0.100 | - |

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

15 Fragen: 13 beantwortet, 2 abgelehnt, 0 Fehler; 13 vom Judge bewertet. Antworten: claude-opus-5-5 (`high`), Judge: claude-sonnet-5-5 (`medium`), Backend `claude-code`. Über das Claude-Abo: Antwortzeiten enthalten den Start der CLI, Kosten sind Schätzungen von Claude Code.

| Frage | Art | Ergebnis | erwartete zitiert | Zitiergenauigkeit | Faithfulness | Sprache | neutral | Zeit |
|---|---|---|---|---|---|---|---|---|
| q01 | de | beantwortet | 3 | 1.000 | 1.000 | ja | - | 7030 ms |
| q02 | de | beantwortet | 0 | 0.909 | 1.000 | ja | - | 12028 ms |
| q04 | fr | beantwortet | 0 | 1.000 | 1.000 | ja | - | 10188 ms |
| q05 | de | beantwortet | 2 | 1.000 | 1.000 | ja | - | 11617 ms |
| q07 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 7538 ms |
| q09 | de | beantwortet | 2 | 1.000 | 1.000 | ja | - | 19664 ms |
| q12 | fr | beantwortet | 1 | 0.923 | 1.000 | ja | - | 11261 ms |
| q13 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 10272 ms |
| q17 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 7282 ms |
| q18 | de | beantwortet | 1 | 0.947 | 1.000 | ja | - | 13184 ms |
| q19 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 10539 ms |
| q26 | wertend | beantwortet | 0 | 1.000 | 1.000 | ja | ja | 10591 ms |
| q28 | wertend | beantwortet | 1 | 1.000 | 1.000 | ja | ja | 12126 ms |
| q29 | unbeantwortbar | abgelehnt (Modell) | - | - | - | ja | - | 4700 ms |
| q32 | unbeantwortbar | abgelehnt (Modell) | - | - | - | ja | - | 3568 ms |

## Verfehlte Quellen (Recall@10 < 1)

- q02 (Recall@10 0.00): transcript:422494 #20, transcript:422531 nicht gefunden
- q04 (Recall@10 0.00): transcript:422506 #11
- q07 (Recall@10 0.50): transcript:418909 #2, business:20244494 #15
- q26 (Recall@10 0.00): transcript:421345 nicht gefunden, transcript:421772 #11, transcript:421630 nicht gefunden
