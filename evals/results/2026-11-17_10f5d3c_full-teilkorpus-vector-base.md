# Eval-Lauf 2026-11-17 07:30 · full (teilkorpus) · vector · base

- Commit: `10f5d3c`
- Goldset: `evals/datasets/golden.jsonl`, 23 Fragen, davon 23 gemessen (0 unbeantwortbare übersprungen)
- Vergleich: kein Vorlauf mit derselben Suite und demselben Modus
- Konfiguration: `chunks_per_query=100`, `retrieval_candidates=50`, `retrieval_rrf_k=60`, `embedding_model=BAAI/bge-m3`, `embedding_max_seq_length=1024`, `index_signature=BAAI/bge-m3|target=500|overlap=0.15|header=1|chunker=v1`, `database=parlrag_exp_base`, `answer_min_similarity=0.55`, `retrieval_rerank=False`
- Korpus: 4'133 Dokumente, 10'477 Chunks

## Metriken

| Metrik | Wert | Vorlauf | Δ |
|---|---|---|---|
| Recall@5 | 0.667 | - | - |
| Recall@10 | 0.833 | - | - |
| Recall@20 | 0.920 | - | - |
| MRR@10 | 0.582 | - | - |
| Suchdauer p50 | 154 ms | - | - |
| Suchdauer p95 | 181 ms | - | - |

## Teilsets

| Teilset | n | Recall@5 | Recall@10 | Recall@20 | MRR@10 | Δ Recall@10 |
|---|---|---|---|---|---|---|
| de | 18 | 0.722 | 0.843 | 0.898 | 0.649 | - |
| fr | 5 | 0.467 | 0.800 | 1.000 | 0.339 | - |
| crosslingual | 4 | 0.250 | 0.500 | 0.875 | 0.119 | - |
| filter | 3 | 1.000 | 1.000 | 1.000 | 1.000 | - |
| teilkorpus | 23 | 0.667 | 0.833 | 0.920 | 0.582 | - |
| wertend | 3 | 0.222 | 0.556 | 0.556 | 0.458 | - |

## Verfehlte Quellen (Recall@10 < 1)

- q02 (Recall@10 0.00): transcript:422494 #18, transcript:422531 nicht gefunden
- q04 (Recall@10 0.00): transcript:422506 #11
- q07 (Recall@10 0.50): transcript:418909 #2, business:20244494 #14
- q26 (Recall@10 0.33): transcript:421345 nicht gefunden, transcript:421772 #8, transcript:421630 nicht gefunden
- q27 (Recall@10 0.33): transcript:419419 #1, transcript:419420 nicht gefunden, transcript:420159 #27
