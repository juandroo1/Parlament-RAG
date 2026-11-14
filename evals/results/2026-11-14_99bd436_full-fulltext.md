# Eval-Lauf 2026-11-14 13:12 · full · fulltext

- Commit: `99bd436`
- Goldset: `evals/datasets/golden.jsonl`, 33 Fragen, davon 28 gemessen (5 unbeantwortbare übersprungen)
- Vergleich: kein Vorlauf mit derselben Suite und demselben Modus
- Konfiguration: `chunks_per_query=100`, `retrieval_candidates=50`, `retrieval_rrf_k=60`, `embedding_model=BAAI/bge-m3`, `embedding_max_seq_length=1024`, `index_signature=BAAI/bge-m3|target=500|overlap=0.15|header=1|chunker=v1`
- Korpus: 42'515 Dokumente, 102'891 Chunks

## Metriken

| Metrik | Wert | Vorlauf | Δ |
|---|---|---|---|
| Recall@5 | 0.292 | - | - |
| Recall@10 | 0.399 | - | - |
| Recall@20 | 0.417 | - | - |
| MRR@10 | 0.270 | - | - |
| Suchdauer p50 | 300 ms | - | - |
| Suchdauer p95 | 1771 ms | - | - |

## Teilsets

| Teilset | n | Recall@5 | Recall@10 | Recall@20 | MRR@10 | Δ Recall@10 |
|---|---|---|---|---|---|---|
| de | 22 | 0.356 | 0.447 | 0.470 | 0.329 | - |
| fr | 6 | 0.056 | 0.222 | 0.222 | 0.054 | - |
| crosslingual | 5 | 0.000 | 0.000 | 0.000 | 0.000 | - |
| filter | 6 | 0.500 | 0.667 | 0.667 | 0.304 | - |
| teilkorpus | 19 | 0.219 | 0.219 | 0.246 | 0.274 | - |
| wertend | 3 | 0.111 | 0.111 | 0.111 | 0.067 | - |

## Verfehlte Quellen (Recall@10 < 1)

- q01 (Recall@10 0.00): transcript:422495 nicht gefunden, transcript:422526 nicht gefunden, transcript:422528 nicht gefunden
- q02 (Recall@10 0.00): transcript:422494 nicht gefunden, transcript:422531 nicht gefunden
- q03 (Recall@10 0.00): transcript:422547 nicht gefunden
- q04 (Recall@10 0.00): transcript:422506 nicht gefunden
- q05 (Recall@10 0.33): transcript:422818 nicht gefunden, transcript:422822 nicht gefunden, transcript:422849 #1
- q07 (Recall@10 0.00): transcript:418909 nicht gefunden, business:20244494 nicht gefunden
- q08 (Recall@10 0.50): transcript:420527 #1, business:20243961 #14
- q10 (Recall@10 0.00): transcript:420159 nicht gefunden
- q11 (Recall@10 0.00): transcript:421772 nicht gefunden
- q12 (Recall@10 0.00): transcript:421775 nicht gefunden
- q13 (Recall@10 0.00): transcript:408632 nicht gefunden
- q14 (Recall@10 0.00): transcript:420393 nicht gefunden, transcript:420430 nicht gefunden
- q16 (Recall@10 0.00): business:20254464 nicht gefunden
- q19 (Recall@10 0.00): transcript:359974 nicht gefunden
- q25 (Recall@10 0.00): transcript:377686 nicht gefunden
- q26 (Recall@10 0.00): transcript:421345 nicht gefunden, transcript:421772 #29, transcript:421630 nicht gefunden
- q27 (Recall@10 0.00): transcript:419419 nicht gefunden, transcript:419420 nicht gefunden, transcript:420159 nicht gefunden
- q28 (Recall@10 0.33): transcript:422704 #5, transcript:422718 nicht gefunden, transcript:422849 nicht gefunden
