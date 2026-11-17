# Eval-Lauf 2026-11-17 07:30 · full (teilkorpus) · vector · c300

- Commit: `10f5d3c`
- Goldset: `evals/datasets/golden.jsonl`, 23 Fragen, davon 23 gemessen (0 unbeantwortbare übersprungen)
- Vergleich: kein Vorlauf mit derselben Suite und demselben Modus
- Konfiguration: `chunks_per_query=100`, `retrieval_candidates=50`, `retrieval_rrf_k=60`, `embedding_model=BAAI/bge-m3`, `embedding_max_seq_length=1024`, `index_signature=BAAI/bge-m3|target=300|overlap=0.15|header=1|chunker=v1`, `database=parlrag_exp_c300`, `answer_min_similarity=0.55`, `retrieval_rerank=False`
- Korpus: 4'133 Dokumente, 13'527 Chunks

## Metriken

| Metrik | Wert | Vorlauf | Δ |
|---|---|---|---|
| Recall@5 | 0.688 | - | - |
| Recall@10 | 0.732 | - | - |
| Recall@20 | 0.906 | - | - |
| MRR@10 | 0.515 | - | - |
| Suchdauer p50 | 169 ms | - | - |
| Suchdauer p95 | 222 ms | - | - |

## Teilsets

| Teilset | n | Recall@5 | Recall@10 | Recall@20 | MRR@10 | Δ Recall@10 |
|---|---|---|---|---|---|---|
| de | 18 | 0.750 | 0.769 | 0.880 | 0.570 | - |
| fr | 5 | 0.467 | 0.600 | 1.000 | 0.317 | - |
| crosslingual | 4 | 0.250 | 0.250 | 0.875 | 0.050 | - |
| filter | 3 | 1.000 | 1.000 | 1.000 | 1.000 | - |
| teilkorpus | 23 | 0.688 | 0.732 | 0.906 | 0.515 | - |
| wertend | 3 | 0.222 | 0.444 | 0.444 | 0.150 | - |

## Verfehlte Quellen (Recall@10 < 1)

- q02 (Recall@10 0.00): transcript:422494 #16, transcript:422531 nicht gefunden
- q04 (Recall@10 0.00): transcript:422506 #12
- q07 (Recall@10 0.50): transcript:418909 #5, business:20244494 #14
- q10 (Recall@10 0.00): transcript:420159 #13
- q16 (Recall@10 0.00): business:20254464 #17
- q26 (Recall@10 0.33): transcript:421345 #29, transcript:421772 #5, transcript:421630 nicht gefunden
- q27 (Recall@10 0.00): transcript:419419 nicht gefunden, transcript:419420 nicht gefunden, transcript:420159 #22
