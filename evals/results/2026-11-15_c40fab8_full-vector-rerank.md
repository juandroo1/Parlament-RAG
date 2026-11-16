# Eval-Lauf 2026-11-15 15:23 · full · vector + Reranker

- Commit: `c40fab8`
- Goldset: `evals/datasets/golden.jsonl`, 65 Fragen, davon 55 gemessen (10 unbeantwortbare übersprungen)
- Vergleich: `2026-11-15_e20e749_full-vector.json` (Commit `e20e749`)
- Konfiguration: `chunks_per_query=100`, `retrieval_candidates=50`, `retrieval_rrf_k=60`, `embedding_model=BAAI/bge-m3`, `embedding_max_seq_length=1024`, `index_signature=BAAI/bge-m3|target=500|overlap=0.15|header=1|chunker=v1`, `answer_min_similarity=0.55`, `retrieval_rerank=True`, `reranker_model=BAAI/bge-reranker-v2-m3`, `rerank_candidates=15`, `reranker_max_length=256`
- Korpus: 42'515 Dokumente, 102'891 Chunks

## Metriken

| Metrik | Wert | Vorlauf | Δ |
|---|---|---|---|
| Recall@5 | 0.671 | 0.671 | ±0.000 |
| Recall@10 | 0.786 | 0.774 | +0.012 |
| Recall@20 | 0.877 | 0.877 | ±0.000 |
| MRR@10 | 0.579 | 0.609 | -0.031 |
| Suchdauer p50 | 12121 ms | 405 ms | +11716 ms |
| Suchdauer p95 | 12388 ms | 1006 ms | +11382 ms |

## Teilsets

| Teilset | n | Recall@5 | Recall@10 | Recall@20 | MRR@10 | Δ Recall@10 |
|---|---|---|---|---|---|---|
| de | 43 | 0.711 | 0.831 | 0.924 | 0.622 | +0.016 |
| fr | 12 | 0.528 | 0.625 | 0.708 | 0.422 | ±0.000 |
| crosslingual | 10 | 0.500 | 0.700 | 0.850 | 0.333 | ±0.000 |
| filter | 8 | 1.000 | 1.000 | 1.000 | 0.875 | ±0.000 |
| teilkorpus | 23 | 0.652 | 0.790 | 0.877 | 0.560 | +0.058 |
| wertend | 5 | 0.200 | 0.333 | 0.533 | 0.450 | -0.033 |

## Schwelle für «keine ausreichende Grundlage»

Schwelle 0.55: fängt 3 von 10 unbeantwortbaren Fragen ohne LLM ab, weist 0 von 55 beantwortbaren fälschlich ab.

| Schwelle | unbeantwortbar abgefangen | beantwortbar fälschlich abgewiesen |
|---|---|---|
| 0.50 | 2 / 10 | 0 / 55 |
| 0.51 | 2 / 10 | 0 / 55 |
| 0.52 | 2 / 10 | 0 / 55 |
| 0.53 | 2 / 10 | 0 / 55 |
| 0.54 | 3 / 10 | 0 / 55 |
| 0.55 (aktuell) | 3 / 10 | 0 / 55 |
| 0.56 | 3 / 10 | 0 / 55 |
| 0.57 | 3 / 10 | 0 / 55 |
| 0.58 | 4 / 10 | 0 / 55 |
| 0.59 | 4 / 10 | 2 / 55 |
| 0.60 | 5 / 10 | 2 / 55 |
| 0.61 | 5 / 10 | 4 / 55 |
| 0.62 | 5 / 10 | 4 / 55 |
| 0.63 | 5 / 10 | 4 / 55 |
| 0.64 | 5 / 10 | 5 / 55 |
| 0.65 | 7 / 10 | 6 / 55 |

## Verfehlte Quellen (Recall@10 < 1)

- q02 (Recall@10 0.00): transcript:422494 #20, transcript:422531 nicht gefunden
- q04 (Recall@10 0.00): transcript:422506 #11
- q07 (Recall@10 0.50): transcript:418909 #5, business:20244494 #15
- q16 (Recall@10 0.00): business:20254464 nicht gefunden
- q21 (Recall@10 0.00): business:20240054 #15
- q26 (Recall@10 0.33): transcript:421345 nicht gefunden, transcript:421772 #1, transcript:421630 nicht gefunden
- q27 (Recall@10 0.33): transcript:419419 #4, transcript:419420 nicht gefunden, transcript:420159 #27
- q38 (Recall@10 0.75): transcript:376534 #2, transcript:376517 #3, transcript:376533 #1, transcript:377134 #27
- q39 (Recall@10 0.50): transcript:374975 #15, business:20250058 #4
- q40 (Recall@10 0.67): transcript:349065 #1, transcript:350076 nicht gefunden, transcript:350226 #2
- q41 (Recall@10 0.50): transcript:337965 #13, business:20224520 #8
- q47 (Recall@10 0.50): business:20244589 #23, transcript:356032 #4
- q48 (Recall@10 0.67): transcript:350891 #3, transcript:350931 nicht gefunden, transcript:358354 #2
- q55 (Recall@10 0.50): transcript:338019 #6, transcript:338005 nicht gefunden
- q57 (Recall@10 0.00): transcript:364190 #35
- q58 (Recall@10 0.00): transcript:354797 #11, transcript:359459 #12
- q59 (Recall@10 0.00): transcript:367133 #25, transcript:374897 nicht gefunden
