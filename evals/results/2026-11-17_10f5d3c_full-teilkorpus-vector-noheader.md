# Eval-Lauf 2026-11-17 07:30 · full (teilkorpus) · vector · noheader

- Commit: `10f5d3c`
- Goldset: `evals/datasets/golden.jsonl`, 23 Fragen, davon 23 gemessen (0 unbeantwortbare übersprungen)
- Vergleich: kein Vorlauf mit derselben Suite und demselben Modus
- Konfiguration: `chunks_per_query=100`, `retrieval_candidates=50`, `retrieval_rrf_k=60`, `embedding_model=BAAI/bge-m3`, `embedding_max_seq_length=1024`, `index_signature=BAAI/bge-m3|target=500|overlap=0.15|header=0|chunker=v1`, `database=parlrag_exp_noheader`, `answer_min_similarity=0.55`, `retrieval_rerank=False`
- Korpus: 4'133 Dokumente, 10'477 Chunks

## Metriken

| Metrik | Wert | Vorlauf | Δ |
|---|---|---|---|
| Recall@5 | 0.623 | - | - |
| Recall@10 | 0.717 | - | - |
| Recall@20 | 0.826 | - | - |
| MRR@10 | 0.547 | - | - |
| Suchdauer p50 | 153 ms | - | - |
| Suchdauer p95 | 172 ms | - | - |

## Teilsets

| Teilset | n | Recall@5 | Recall@10 | Recall@20 | MRR@10 | Δ Recall@10 |
|---|---|---|---|---|---|---|
| de | 18 | 0.593 | 0.694 | 0.833 | 0.590 | - |
| fr | 5 | 0.733 | 0.800 | 0.800 | 0.390 | - |
| crosslingual | 4 | 0.000 | 0.250 | 0.500 | 0.036 | - |
| filter | 3 | 0.833 | 1.000 | 1.000 | 1.000 | - |
| teilkorpus | 23 | 0.623 | 0.717 | 0.826 | 0.547 | - |
| wertend | 3 | 0.333 | 0.556 | 0.667 | 0.187 | - |

## Verfehlte Quellen (Recall@10 < 1)

- q01 (Recall@10 0.00): transcript:422495 #26, transcript:422526 nicht gefunden, transcript:422528 nicht gefunden
- q02 (Recall@10 0.00): transcript:422494 nicht gefunden, transcript:422531 nicht gefunden
- q04 (Recall@10 0.00): transcript:422506 #23
- q05 (Recall@10 0.33): transcript:422818 #18, transcript:422822 #11, transcript:422849 #1
- q07 (Recall@10 0.50): transcript:418909 #11, business:20244494 #1
- q13 (Recall@10 0.00): transcript:408632 #11
- q26 (Recall@10 0.33): transcript:421345 #19, transcript:421772 #5, transcript:421630 nicht gefunden
- q27 (Recall@10 0.33): transcript:419419 #9, transcript:419420 nicht gefunden, transcript:420159 #40
