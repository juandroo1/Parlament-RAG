# Eval-Lauf 2026-11-17 07:30 · full (teilkorpus) · vector · c800

- Commit: `10f5d3c`
- Goldset: `evals/datasets/golden.jsonl`, 23 Fragen, davon 23 gemessen (0 unbeantwortbare übersprungen)
- Vergleich: kein Vorlauf mit derselben Suite und demselben Modus
- Konfiguration: `chunks_per_query=100`, `retrieval_candidates=50`, `retrieval_rrf_k=60`, `embedding_model=BAAI/bge-m3`, `embedding_max_seq_length=1024`, `index_signature=BAAI/bge-m3|target=800|overlap=0.15|header=1|chunker=v1`, `database=parlrag_exp_c800`, `answer_min_similarity=0.55`, `retrieval_rerank=False`
- Korpus: 4'133 Dokumente, 8'928 Chunks

## Metriken

| Metrik | Wert | Vorlauf | Δ |
|---|---|---|---|
| Recall@5 | 0.638 | - | - |
| Recall@10 | 0.725 | - | - |
| Recall@20 | 0.906 | - | - |
| MRR@10 | 0.521 | - | - |
| Suchdauer p50 | 144 ms | - | - |
| Suchdauer p95 | 166 ms | - | - |

## Teilsets

| Teilset | n | Recall@5 | Recall@10 | Recall@20 | MRR@10 | Δ Recall@10 |
|---|---|---|---|---|---|---|
| de | 18 | 0.704 | 0.778 | 0.880 | 0.574 | - |
| fr | 5 | 0.400 | 0.533 | 1.000 | 0.329 | - |
| crosslingual | 4 | 0.250 | 0.250 | 0.875 | 0.062 | - |
| filter | 3 | 1.000 | 1.000 | 1.000 | 1.000 | - |
| teilkorpus | 23 | 0.638 | 0.725 | 0.906 | 0.521 | - |
| wertend | 3 | 0.000 | 0.222 | 0.444 | 0.048 | - |

## Verfehlte Quellen (Recall@10 < 1)

- q02 (Recall@10 0.00): transcript:422494 #17, transcript:422531 nicht gefunden
- q04 (Recall@10 0.00): transcript:422506 #11
- q10 (Recall@10 0.00): transcript:420159 #15
- q16 (Recall@10 0.00): business:20254464 #14
- q26 (Recall@10 0.00): transcript:421345 #21, transcript:421772 #17, transcript:421630 nicht gefunden
- q27 (Recall@10 0.00): transcript:419419 nicht gefunden, transcript:419420 nicht gefunden, transcript:420159 #22
- q28 (Recall@10 0.67): transcript:422704 #8, transcript:422718 #12, transcript:422849 #7
