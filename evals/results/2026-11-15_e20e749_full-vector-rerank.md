# Eval-Lauf 2026-11-15 13:26 · full · vector + Reranker

- Commit: `e20e749`
- Goldset: `evals/datasets/golden.jsonl`, 65 Fragen, davon 55 gemessen (10 unbeantwortbare übersprungen)
- Vergleich: `2026-11-15_e20e749_full-vector.json` (Commit `e20e749`)
- Konfiguration: `chunks_per_query=100`, `retrieval_candidates=50`, `retrieval_rrf_k=60`, `embedding_model=BAAI/bge-m3`, `embedding_max_seq_length=1024`, `index_signature=BAAI/bge-m3|target=500|overlap=0.15|header=1|chunker=v1`, `answer_min_similarity=0.55`, `retrieval_rerank=True`, `reranker_model=BAAI/bge-reranker-v2-m3`, `rerank_candidates=30`
- Korpus: 42'515 Dokumente, 102'891 Chunks

## Metriken

| Metrik | Wert | Vorlauf | Δ |
|---|---|---|---|
| Recall@5 | 0.668 | 0.671 | -0.003 |
| Recall@10 | 0.826 | 0.774 | +0.052 |
| Recall@20 | 0.868 | 0.877 | -0.009 |
| MRR@10 | 0.596 | 0.609 | -0.013 |
| Suchdauer p50 | 27528 ms | 405 ms | +27123 ms |
| Suchdauer p95 | 28902 ms | 1006 ms | +27896 ms |

## Teilsets

| Teilset | n | Recall@5 | Recall@10 | Recall@20 | MRR@10 | Δ Recall@10 |
|---|---|---|---|---|---|---|
| de | 43 | 0.719 | 0.866 | 0.913 | 0.635 | +0.050 |
| fr | 12 | 0.486 | 0.681 | 0.708 | 0.458 | +0.056 |
| crosslingual | 10 | 0.400 | 0.800 | 0.850 | 0.249 | +0.100 |
| filter | 8 | 1.000 | 1.000 | 1.000 | 0.844 | ±0.000 |
| teilkorpus | 23 | 0.623 | 0.812 | 0.877 | 0.566 | +0.080 |
| wertend | 5 | 0.133 | 0.200 | 0.333 | 0.300 | -0.167 |

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

- q01 (Recall@10 0.67): transcript:422495 #10, transcript:422526 #12, transcript:422528 #5
- q02 (Recall@10 0.00): transcript:422494 #20, transcript:422531 nicht gefunden
- q16 (Recall@10 0.00): business:20254464 nicht gefunden
- q26 (Recall@10 0.33): transcript:421345 nicht gefunden, transcript:421772 #2, transcript:421630 nicht gefunden
- q27 (Recall@10 0.00): transcript:419419 #15, transcript:419420 nicht gefunden, transcript:420159 #27
- q28 (Recall@10 0.67): transcript:422704 #1, transcript:422718 #12, transcript:422849 #7
- q38 (Recall@10 0.75): transcript:376534 #2, transcript:376517 #4, transcript:376533 #1, transcript:377134 #27
- q39 (Recall@10 0.50): transcript:374975 #18, business:20250058 #6
- q40 (Recall@10 0.67): transcript:349065 #2, transcript:350076 nicht gefunden, transcript:350226 #4
- q42 (Recall@10 0.67): transcript:339957 #1, transcript:339965 #11, transcript:339995 #9
- q48 (Recall@10 0.67): transcript:350891 #1, transcript:350931 nicht gefunden, transcript:358354 #3
- q55 (Recall@10 0.50): transcript:338019 #2, transcript:338005 nicht gefunden
- q57 (Recall@10 0.00): transcript:364190 #35
- q58 (Recall@10 0.00): transcript:354797 #22, transcript:359459 #23
- q59 (Recall@10 0.00): transcript:367133 #25, transcript:374897 nicht gefunden
