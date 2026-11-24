# Eval-Lauf 2026-11-24 14:34 · smoke · vector

- Commit: `7ab0f77`
- Goldset: `evals/datasets/golden.jsonl`, 15 Fragen, davon 13 gemessen (2 unbeantwortbare übersprungen)
- Vergleich: `2026-11-24_71904f2_smoke-vector.json` (Commit `71904f2`)
- Konfiguration: `chunks_per_query=100`, `retrieval_candidates=50`, `retrieval_rrf_k=60`, `embedding_model=BAAI/bge-m3`, `embedding_max_seq_length=1024`, `index_signature=BAAI/bge-m3|target=500|overlap=0.15|header=1|chunker=v1`, `database=parlrag`, `answer_min_similarity=0.55`, `retrieval_rerank=False`, `query_detection=True`
- Korpus: 42'515 Dokumente, 102'891 Chunks

## Metriken

| Metrik | Wert | Vorlauf | Δ |
|---|---|---|---|
| Recall@5 | 0.756 | 0.577 | +0.179 |
| Recall@10 | 0.808 | 0.731 | +0.077 |
| Recall@20 | 0.910 | 0.910 | ±0.000 |
| MRR@10 | 0.556 | 0.389 | +0.167 |
| Suchdauer p50 | 176 ms | 183 ms | -7 ms |
| Suchdauer p95 | 287 ms | 228 ms | +60 ms |

## Teilsets

| Teilset | n | Recall@5 | Recall@10 | Recall@20 | MRR@10 | Δ Recall@10 |
|---|---|---|---|---|---|---|
| de | 10 | 0.750 | 0.750 | 0.883 | 0.553 | ±0.000 |
| fr | 3 | 0.778 | 1.000 | 1.000 | 0.567 | +0.333 |
| crosslingual | 4 | 0.750 | 0.750 | 0.875 | 0.333 | +0.250 |
| filter | 2 | 1.000 | 1.000 | 1.000 | 1.000 | ±0.000 |
| teilkorpus | 10 | 0.683 | 0.750 | 0.883 | 0.570 | +0.100 |
| wertend | 2 | 0.167 | 0.500 | 0.667 | 0.100 | ±0.000 |

## Schwelle für «keine ausreichende Grundlage»

Schwelle 0.55: fängt 0 von 1 unbeantwortbaren Fragen ohne LLM ab, weist 0 von 13 beantwortbaren fälschlich ab.

| Schwelle | unbeantwortbar abgefangen | beantwortbar fälschlich abgewiesen |
|---|---|---|
| 0.50 | 0 / 1 | 0 / 13 |
| 0.51 | 0 / 1 | 0 / 13 |
| 0.52 | 0 / 1 | 0 / 13 |
| 0.53 | 0 / 1 | 0 / 13 |
| 0.54 | 0 / 1 | 0 / 13 |
| 0.55 (aktuell) | 0 / 1 | 0 / 13 |
| 0.56 | 0 / 1 | 0 / 13 |
| 0.57 | 0 / 1 | 1 / 13 |
| 0.58 | 0 / 1 | 2 / 13 |
| 0.59 | 0 / 1 | 2 / 13 |
| 0.60 | 0 / 1 | 3 / 13 |
| 0.61 | 0 / 1 | 3 / 13 |
| 0.62 | 0 / 1 | 3 / 13 |
| 0.63 | 0 / 1 | 3 / 13 |
| 0.64 | 0 / 1 | 3 / 13 |
| 0.65 | 1 / 1 | 3 / 13 |

## Verfehlte Quellen (Recall@10 < 1)

- q02 (Recall@10 0.00): transcript:422494 #20, transcript:422531 nicht gefunden
- q07 (Recall@10 0.50): transcript:418909 #2, business:20244494 #15
- q26 (Recall@10 0.00): transcript:421345 nicht gefunden, transcript:421772 #11, transcript:421630 nicht gefunden
