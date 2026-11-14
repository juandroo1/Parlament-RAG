# Eval-Lauf 2026-11-14 13:00 · full · hybrid

- Commit: `d8f9fa2`
- Goldset: `evals/datasets/golden.jsonl`, 33 Fragen, davon 28 gemessen (5 unbeantwortbare übersprungen)
- Vergleich: kein Vorlauf mit derselben Suite und demselben Modus
- Konfiguration: `chunks_per_query=100`, `retrieval_candidates=50`, `retrieval_rrf_k=60`, `embedding_model=BAAI/bge-m3`, `embedding_max_seq_length=1024`, `index_signature=BAAI/bge-m3|target=500|overlap=0.15|header=1|chunker=v1`
- Korpus: 42'515 Dokumente, 102'891 Chunks

## Metriken

| Metrik | Wert | Vorlauf | Δ |
|---|---|---|---|
| Recall@5 | 0.512 | - | - |
| Recall@10 | 0.637 | - | - |
| Recall@20 | 0.827 | - | - |
| MRR@10 | 0.424 | - | - |
| Suchdauer p50 | 551 ms | - | - |
| Suchdauer p95 | 1246 ms | - | - |

## Teilsets

| Teilset | n | Recall@5 | Recall@10 | Recall@20 | MRR@10 | Δ Recall@10 |
|---|---|---|---|---|---|---|
| de | 22 | 0.545 | 0.705 | 0.871 | 0.497 | - |
| fr | 6 | 0.389 | 0.389 | 0.667 | 0.153 | - |
| crosslingual | 5 | 0.000 | 0.000 | 0.600 | 0.000 | - |
| filter | 6 | 0.917 | 1.000 | 1.000 | 0.631 | - |
| teilkorpus | 19 | 0.439 | 0.570 | 0.746 | 0.370 | - |
| wertend | 3 | 0.222 | 0.333 | 0.556 | 0.256 | - |

## Verfehlte Quellen (Recall@10 < 1)

- q01 (Recall@10 0.67): transcript:422495 #5, transcript:422526 #15, transcript:422528 #7
- q02 (Recall@10 0.00): transcript:422494 #47, transcript:422531 nicht gefunden
- q04 (Recall@10 0.00): transcript:422506 #26
- q05 (Recall@10 0.67): transcript:422818 #10, transcript:422822 #12, transcript:422849 #1
- q07 (Recall@10 0.50): transcript:418909 #4, business:20244494 #31
- q10 (Recall@10 0.00): transcript:420159 #14
- q13 (Recall@10 0.00): transcript:408632 #17
- q16 (Recall@10 0.00): business:20254464 nicht gefunden
- q19 (Recall@10 0.00): transcript:359974 #11
- q25 (Recall@10 0.00): transcript:377686 #11
- q26 (Recall@10 0.33): transcript:421345 nicht gefunden, transcript:421772 #3, transcript:421630 nicht gefunden
- q27 (Recall@10 0.33): transcript:419419 #10, transcript:419420 nicht gefunden, transcript:420159 #53
- q28 (Recall@10 0.33): transcript:422704 #3, transcript:422718 #15, transcript:422849 #17
