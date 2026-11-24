# Eval-Lauf 2026-11-24 14:37 · full (person-zeit) · vector · haiku-low-detect

- Commit: `7ab0f77`
- Goldset: `evals/datasets/golden.jsonl`, 17 Fragen, davon 11 gemessen (6 unbeantwortbare übersprungen)
- Vergleich: `2026-11-24_5db9a91_full-person-zeit-vector-haiku-low-answers.json` (Commit `5db9a91`)
- Konfiguration: `chunks_per_query=100`, `retrieval_candidates=50`, `retrieval_rrf_k=60`, `embedding_model=BAAI/bge-m3`, `embedding_max_seq_length=1024`, `index_signature=BAAI/bge-m3|target=500|overlap=0.15|header=1|chunker=v1`, `database=parlrag`, `answer_min_similarity=0.55`, `retrieval_rerank=False`, `query_detection=True`
- Korpus: 42'515 Dokumente, 102'891 Chunks

## Metriken

| Metrik | Wert | Vorlauf | Δ |
|---|---|---|---|
| Recall@5 | 0.841 | 0.591 | +0.250 |
| Recall@10 | 0.955 | 0.750 | +0.205 |
| Recall@20 | 0.955 | 0.841 | +0.114 |
| MRR@10 | 0.874 | 0.617 | +0.256 |
| Suchdauer p50 | 169 ms | 151 ms | +19 ms |
| Suchdauer p95 | 240 ms | 192 ms | +47 ms |
| Zitiergenauigkeit | 0.960 | 0.967 | -0.008 |
| Faithfulness | 0.967 | 0.990 | -0.023 |
| Ablehnungsquote (unbeantwortbar) | 1.000 | 1.000 | ±0.000 |
| Ausserhalb erkannt, ohne LLM | 1.000 | 0.000 | +1.000 |
| Falsche Ablehnungen | 0.000 | 0.091 | -0.091 |
| Antwortsprache | 1.000 | 1.000 | ±0.000 |
| Antwortzeit p50 | 5330 ms | 6169 ms | -839 ms |
| Antwortzeit p95 | 12216 ms | 13053 ms | -837 ms |
| Kosten Antwort pro Frage | 0.0015 USD | 0.0021 USD | -0.0006 USD |
| Kosten Judge pro Frage | 0.0396 USD | 0.0397 USD | -0.0001 USD |

## Teilsets

| Teilset | n | Recall@5 | Recall@10 | Recall@20 | MRR@10 | Δ Recall@10 |
|---|---|---|---|---|---|---|
| de | 7 | 0.893 | 0.929 | 0.929 | 0.929 | +0.107 |
| fr | 4 | 0.750 | 1.000 | 1.000 | 0.778 | +0.375 |
| crosslingual | 2 | 0.500 | 1.000 | 1.000 | 0.556 | +0.500 |
| person-zeit | 11 | 0.841 | 0.955 | 0.955 | 0.874 | +0.205 |

## Antworten

17 Fragen: 11 beantwortet, 6 abgelehnt, 0 Fehler; 11 vom Judge bewertet. Antworten: claude-haiku-5-5 (`low`), Judge: claude-sonnet-5-5 (`medium`), Backend `claude-code`. Über das Claude-Abo: Antwortzeiten enthalten den Start der CLI, Kosten sind Schätzungen von Claude Code.

| Frage | Art | Ergebnis | erwartete zitiert | Zitiergenauigkeit | Faithfulness | Sprache | neutral | Zeit |
|---|---|---|---|---|---|---|---|---|
| q29 | unbeantwortbar | abgelehnt (ausserhalb des Datenbestands) | - | - | - | ja | - | 0 ms |
| q62 | unbeantwortbar | abgelehnt (ausserhalb des Datenbestands) | - | - | - | ja | - | 0 ms |
| q66 | de | beantwortet | 2 | 0.833 | 0.833 | ja | - | 5330 ms |
| q67 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 4669 ms |
| q68 | fr | beantwortet | 2 | 1.000 | 1.000 | ja | - | 10952 ms |
| q69 | de | beantwortet | 3 | 1.000 | 1.000 | ja | - | 9553 ms |
| q70 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 5851 ms |
| q71 | fr | beantwortet | 0 | 1.000 | 1.000 | ja | - | 7462 ms |
| q72 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 11485 ms |
| q73 | de | beantwortet | 1 | 0.800 | 0.800 | ja | - | 4502 ms |
| q74 | de | beantwortet | 2 | 0.923 | 1.000 | ja | - | 7800 ms |
| q75 | fr | beantwortet | 3 | 1.000 | 1.000 | ja | - | 12216 ms |
| q76 | fr | beantwortet | 1 | 1.000 | 1.000 | ja | - | 10440 ms |
| q77 | unbeantwortbar | abgelehnt (ausserhalb des Datenbestands) | - | - | - | ja | - | 1 ms |
| q78 | unbeantwortbar | abgelehnt (ausserhalb des Datenbestands) | - | - | - | ja | - | 1 ms |
| q79 | unbeantwortbar | abgelehnt (ausserhalb des Datenbestands) | - | - | - | ja | - | 1 ms |
| q80 | unbeantwortbar | abgelehnt (ausserhalb des Datenbestands) | - | - | - | ja | - | 0 ms |

## Verfehlte Quellen (Recall@10 < 1)

- q70 (Recall@10 0.50): transcript:338625 #1, transcript:339318 #30
