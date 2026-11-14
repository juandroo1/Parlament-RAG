# Eval-Lauf 2026-11-14 13:18 · smoke · vector

- Commit: `c4db393`
- Goldset: `evals/datasets/golden.jsonl`, 15 Fragen, davon 13 gemessen (2 unbeantwortbare übersprungen)
- Vergleich: `2026-11-14_d8f9fa2_smoke-hybrid.json` (Commit `d8f9fa2`)
- Konfiguration: `chunks_per_query=100`, `retrieval_candidates=50`, `retrieval_rrf_k=60`, `embedding_model=BAAI/bge-m3`, `embedding_max_seq_length=1024`, `index_signature=BAAI/bge-m3|target=500|overlap=0.15|header=1|chunker=v1`
- Korpus: 42'515 Dokumente, 102'891 Chunks

## Metriken

| Metrik | Wert | Vorlauf | Δ |
|---|---|---|---|
| Recall@5 | 0.577 | 0.449 | +0.128 |
| Recall@10 | 0.731 | 0.500 | +0.231 |
| Recall@20 | 0.910 | 0.756 | +0.154 |
| MRR@10 | 0.389 | 0.362 | +0.028 |
| Suchdauer p50 | 370 ms | 1044 ms | -674 ms |
| Suchdauer p95 | 708 ms | 4563 ms | -3854 ms |

## Teilsets

| Teilset | n | Recall@5 | Recall@10 | Recall@20 | MRR@10 | Δ Recall@10 |
|---|---|---|---|---|---|---|
| de | 10 | 0.617 | 0.750 | 0.883 | 0.386 | +0.233 |
| fr | 3 | 0.444 | 0.667 | 1.000 | 0.400 | +0.222 |
| crosslingual | 4 | 0.250 | 0.500 | 0.875 | 0.081 | +0.500 |
| filter | 2 | 1.000 | 1.000 | 1.000 | 1.000 | ±0.000 |
| teilkorpus | 10 | 0.450 | 0.650 | 0.883 | 0.366 | +0.200 |
| wertend | 2 | 0.167 | 0.500 | 0.667 | 0.100 | +0.167 |

## Verfehlte Quellen (Recall@10 < 1)

- q02 (Recall@10 0.00): transcript:422494 #20, transcript:422531 nicht gefunden
- q04 (Recall@10 0.00): transcript:422506 #11
- q07 (Recall@10 0.50): transcript:418909 #2, business:20244494 #15
- q26 (Recall@10 0.00): transcript:421345 nicht gefunden, transcript:421772 #11, transcript:421630 nicht gefunden
