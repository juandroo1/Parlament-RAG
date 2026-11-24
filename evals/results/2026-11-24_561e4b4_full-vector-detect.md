# Eval-Lauf 2026-11-24 14:32 · full · vector · detect

- Commit: `561e4b4`
- Goldset: `evals/datasets/golden.jsonl`, 80 Fragen, davon 66 gemessen (14 unbeantwortbare übersprungen)
- Vergleich: `2026-11-24_2605d57_full-vector.json` (Commit `2605d57`)
- Konfiguration: `chunks_per_query=100`, `retrieval_candidates=50`, `retrieval_rrf_k=60`, `embedding_model=BAAI/bge-m3`, `embedding_max_seq_length=1024`, `index_signature=BAAI/bge-m3|target=500|overlap=0.15|header=1|chunker=v1`, `database=parlrag`, `answer_min_similarity=0.55`, `retrieval_rerank=False`, `query_detection=True`, `query_detection_strip=False`
- Korpus: 42'515 Dokumente, 102'891 Chunks

## Metriken

| Metrik | Wert | Vorlauf | Δ |
|---|---|---|---|
| Recall@5 | 0.783 | 0.658 | +0.125 |
| Recall@10 | 0.840 | 0.770 | +0.069 |
| Recall@20 | 0.905 | 0.871 | +0.034 |
| MRR@10 | 0.728 | 0.611 | +0.118 |
| Suchdauer p50 | 183 ms | 345 ms | -162 ms |
| Suchdauer p95 | 384 ms | 734 ms | -350 ms |

## Teilsets

| Teilset | n | Recall@5 | Recall@10 | Recall@20 | MRR@10 | Δ Recall@10 |
|---|---|---|---|---|---|---|
| de | 50 | 0.817 | 0.838 | 0.925 | 0.779 | +0.022 |
| fr | 16 | 0.677 | 0.844 | 0.844 | 0.570 | +0.219 |
| crosslingual | 12 | 0.750 | 0.917 | 0.958 | 0.535 | +0.250 |
| filter | 8 | 1.000 | 1.000 | 1.000 | 1.000 | ±0.000 |
| teilkorpus | 23 | 0.725 | 0.775 | 0.877 | 0.654 | +0.043 |
| wertend | 5 | 0.233 | 0.367 | 0.533 | 0.290 | ±0.000 |
| person-zeit | 11 | 0.841 | 0.955 | 0.955 | 0.874 | +0.205 |

## Schwelle für «keine ausreichende Grundlage»

Schwelle 0.55: fängt 3 von 8 unbeantwortbaren Fragen ohne LLM ab, weist 0 von 66 beantwortbaren fälschlich ab.

| Schwelle | unbeantwortbar abgefangen | beantwortbar fälschlich abgewiesen |
|---|---|---|
| 0.50 | 2 / 8 | 0 / 66 |
| 0.51 | 2 / 8 | 0 / 66 |
| 0.52 | 2 / 8 | 0 / 66 |
| 0.53 | 2 / 8 | 0 / 66 |
| 0.54 | 3 / 8 | 0 / 66 |
| 0.55 (aktuell) | 3 / 8 | 0 / 66 |
| 0.56 | 3 / 8 | 0 / 66 |
| 0.57 | 3 / 8 | 3 / 66 |
| 0.58 | 5 / 8 | 4 / 66 |
| 0.59 | 5 / 8 | 4 / 66 |
| 0.60 | 5 / 8 | 5 / 66 |
| 0.61 | 5 / 8 | 8 / 66 |
| 0.62 | 5 / 8 | 10 / 66 |
| 0.63 | 5 / 8 | 11 / 66 |
| 0.64 | 5 / 8 | 11 / 66 |
| 0.65 | 7 / 8 | 13 / 66 |

## Verfehlte Quellen (Recall@10 < 1)

- q02 (Recall@10 0.00): transcript:422494 #20, transcript:422531 nicht gefunden
- q07 (Recall@10 0.50): transcript:418909 #2, business:20244494 #15
- q16 (Recall@10 0.00): business:20254464 nicht gefunden
- q21 (Recall@10 0.00): business:20240054 #15
- q26 (Recall@10 0.00): transcript:421345 nicht gefunden, transcript:421772 #11, transcript:421630 nicht gefunden
- q27 (Recall@10 0.33): transcript:419419 #1, transcript:419420 nicht gefunden, transcript:420159 #27
- q34 (Recall@10 0.00): business:20260025 #12
- q38 (Recall@10 0.75): transcript:376534 #1, transcript:376517 #3, transcript:376533 #4, transcript:377134 #27
- q39 (Recall@10 0.50): transcript:374975 #15, business:20250058 #3
- q40 (Recall@10 0.67): transcript:349065 #1, transcript:350076 nicht gefunden, transcript:350226 #5
- q47 (Recall@10 0.50): business:20244589 #23, transcript:356032 #1
- q48 (Recall@10 0.67): transcript:350891 #4, transcript:350931 #23, transcript:358354 #1
- q55 (Recall@10 0.50): transcript:338019 #2, transcript:338005 nicht gefunden
- q58 (Recall@10 0.50): transcript:354797 #4, transcript:359459 #12
- q59 (Recall@10 0.00): transcript:367133 #25, transcript:374897 nicht gefunden
- q70 (Recall@10 0.50): transcript:338625 #1, transcript:339318 #30
