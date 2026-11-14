# Eval-Lauf 2026-11-14 16:41 · full · vector

- Commit: `a201a9c`
- Goldset: `evals/datasets/golden.jsonl`, 65 Fragen, davon 55 gemessen (10 unbeantwortbare übersprungen)
- Vergleich: kein Vorlauf mit derselben Suite und demselben Modus
- Konfiguration: `chunks_per_query=100`, `retrieval_candidates=50`, `retrieval_rrf_k=60`, `embedding_model=BAAI/bge-m3`, `embedding_max_seq_length=1024`, `index_signature=BAAI/bge-m3|target=500|overlap=0.15|header=1|chunker=v1`, `answer_min_similarity=0.55`
- Korpus: 42'515 Dokumente, 102'891 Chunks

## Metriken

| Metrik | Wert | Vorlauf | Δ |
|---|---|---|---|
| Recall@5 | 0.671 | - | - |
| Recall@10 | 0.774 | - | - |
| Recall@20 | 0.877 | - | - |
| MRR@10 | 0.609 | - | - |
| Suchdauer p50 | 283 ms | - | - |
| Suchdauer p95 | 621 ms | - | - |
| Zitiergenauigkeit | 0.976 | - | - |
| Faithfulness | 0.979 | - | - |
| Ablehnungsquote (unbeantwortbar) | 0.900 | - | - |
| Falsche Ablehnungen | 0.020 | - | - |
| Neutralität (wertend) | 1.000 | - | - |
| Antwortsprache | 0.985 | - | - |
| Antwortzeit p50 | 6040 ms | - | - |
| Antwortzeit p95 | 12696 ms | - | - |
| Kosten Antwort pro Frage | 0.0017 USD | - | - |
| Kosten Judge pro Frage | 0.0390 USD | - | - |

## Teilsets

| Teilset | n | Recall@5 | Recall@10 | Recall@20 | MRR@10 | Δ Recall@10 |
|---|---|---|---|---|---|---|
| de | 43 | 0.723 | 0.816 | 0.924 | 0.678 | - |
| fr | 12 | 0.486 | 0.625 | 0.708 | 0.362 | - |
| crosslingual | 10 | 0.400 | 0.700 | 0.850 | 0.241 | - |
| filter | 8 | 1.000 | 1.000 | 1.000 | 0.938 | - |
| teilkorpus | 23 | 0.580 | 0.732 | 0.877 | 0.538 | - |
| wertend | 5 | 0.233 | 0.367 | 0.533 | 0.290 | - |

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

## Antworten

65 Fragen: 55 beantwortet, 10 abgelehnt, 0 Fehler; 55 vom Judge bewertet. Antworten: claude-haiku-5-5 (`low`), Judge: claude-sonnet-5-5 (`medium`), Backend `claude-code`. Über das Claude-Abo: Antwortzeiten enthalten den Start der CLI, Kosten sind Schätzungen von Claude Code.

| Frage | Art | Ergebnis | erwartete zitiert | Zitiergenauigkeit | Faithfulness | Sprache | neutral | Zeit |
|---|---|---|---|---|---|---|---|---|
| q01 | de | beantwortet | 3 | 1.000 | 1.000 | ja | - | 6588 ms |
| q02 | de | beantwortet | 0 | 1.000 | 1.000 | ja | - | 11149 ms |
| q03 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 9247 ms |
| q04 | fr | beantwortet | 0 | 1.000 | 1.000 | ja | - | 5838 ms |
| q05 | de | beantwortet | 3 | 1.000 | 1.000 | ja | - | 6018 ms |
| q06 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 4242 ms |
| q07 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 5549 ms |
| q08 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 10379 ms |
| q09 | de | beantwortet | 2 | 1.000 | 1.000 | ja | - | 12986 ms |
| q10 | de | beantwortet | 0 | 1.000 | 1.000 | ja | - | 5514 ms |
| q11 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 4072 ms |
| q12 | fr | beantwortet | 1 | 0.800 | 1.000 | nein | - | 8065 ms |
| q13 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 8019 ms |
| q14 | de | beantwortet | 2 | 1.000 | 1.000 | ja | - | 9513 ms |
| q15 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 3893 ms |
| q16 | fr | beantwortet | 0 | 1.000 | 0.812 | ja | - | 11352 ms |
| q17 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 6040 ms |
| q18 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 13729 ms |
| q19 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 8342 ms |
| q20 | de | beantwortet | 1 | 1.000 | 0.917 | ja | - | 6020 ms |
| q21 | de | beantwortet | 0 | 1.000 | 0.833 | ja | - | 4359 ms |
| q22 | de | beantwortet | 1 | 0.846 | 0.938 | ja | - | 4481 ms |
| q23 | de | beantwortet | 1 | 0.750 | 0.750 | ja | - | 3696 ms |
| q24 | fr | beantwortet | 1 | 1.000 | 1.000 | ja | - | 12121 ms |
| q25 | fr | beantwortet | 1 | 1.000 | 1.000 | ja | - | 8978 ms |
| q26 | wertend | beantwortet | 0 | 0.889 | 1.000 | ja | ja | 11645 ms |
| q27 | wertend | beantwortet | 1 | 1.000 | 1.000 | ja | ja | 12696 ms |
| q28 | wertend | beantwortet | 1 | 1.000 | 1.000 | ja | ja | 9862 ms |
| q29 | unbeantwortbar | abgelehnt (Modell) | - | - | - | ja | - | 3367 ms |
| q30 | unbeantwortbar | abgelehnt (Schwelle) | - | - | - | ja | - | 382 ms |
| q31 | unbeantwortbar | abgelehnt (Modell) | - | - | - | ja | - | 3324 ms |
| q32 | unbeantwortbar | abgelehnt (Modell) | - | - | - | ja | - | 2894 ms |
| q33 | unbeantwortbar | abgelehnt (Schwelle) | - | - | - | ja | - | 290 ms |
| q34 | de | beantwortet | 0 | 1.000 | 1.000 | ja | - | 2996 ms |
| q35 | de | beantwortet | 2 | 1.000 | 1.000 | ja | - | 5957 ms |
| q36 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 6352 ms |
| q37 | de | beantwortet | 2 | 1.000 | 1.000 | ja | - | 6723 ms |
| q38 | de | beantwortet | 3 | 1.000 | 0.944 | ja | - | 8915 ms |
| q39 | de | beantwortet | 1 | 0.857 | 1.000 | ja | - | 8194 ms |
| q40 | de | beantwortet | 2 | 1.000 | 0.929 | ja | - | 4808 ms |
| q41 | de | beantwortet | 2 | 1.000 | 1.000 | ja | - | 3947 ms |
| q42 | de | beantwortet | 2 | 1.000 | 1.000 | ja | - | 4825 ms |
| q43 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 10188 ms |
| q44 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 6874 ms |
| q45 | de | beantwortet | 2 | 0.833 | 1.000 | ja | - | 3576 ms |
| q46 | de | beantwortet | 2 | 1.000 | 0.929 | ja | - | 6525 ms |
| q47 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 7489 ms |
| q48 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 5630 ms |
| q49 | de | beantwortet | 1 | 1.000 | 0.900 | ja | - | 15948 ms |
| q50 | de | beantwortet | 2 | 1.000 | 1.000 | ja | - | 5939 ms |
| q51 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 8356 ms |
| q52 | de | beantwortet | 1 | 1.000 | 1.000 | ja | - | 4608 ms |
| q53 | fr | beantwortet | 1 | 1.000 | 1.000 | ja | - | 4099 ms |
| q54 | fr | beantwortet | 0 | 1.000 | 1.000 | ja | - | 9743 ms |
| q55 | fr | beantwortet | 1 | 1.000 | 0.917 | ja | - | 8346 ms |
| q56 | fr | beantwortet | 1 | 0.857 | 1.000 | ja | - | 7614 ms |
| q57 | fr | abgelehnt (Modell) | - | - | - | ja | - | 3243 ms |
| q58 | wertend | beantwortet | 1 | 1.000 | 0.955 | ja | ja | 8403 ms |
| q59 | wertend | beantwortet | 0 | 0.857 | 1.000 | ja | ja | 8921 ms |
| q60 | unbeantwortbar | abgelehnt (Modell) | - | - | - | ja | - | 2478 ms |
| q61 | unbeantwortbar | abgelehnt (Modell) | - | - | - | ja | - | 2571 ms |
| q62 | unbeantwortbar | abgelehnt (Modell) | - | - | - | ja | - | 3155 ms |
| q63 | unbeantwortbar | beantwortet | - | 1.000 | 1.000 | ja | - | 8177 ms |
| q64 | unbeantwortbar | abgelehnt (Schwelle) | - | - | - | ja | - | 190 ms |
| q65 | de | beantwortet | 2 | 1.000 | 1.000 | ja | - | 5907 ms |

## Verfehlte Quellen (Recall@10 < 1)

- q02 (Recall@10 0.00): transcript:422494 #20, transcript:422531 nicht gefunden
- q04 (Recall@10 0.00): transcript:422506 #11
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
- q48 (Recall@10 0.33): transcript:350891 #11, transcript:350931 nicht gefunden, transcript:358354 #1
- q55 (Recall@10 0.50): transcript:338019 #2, transcript:338005 nicht gefunden
- q57 (Recall@10 0.00): transcript:364190 #35
- q58 (Recall@10 0.50): transcript:354797 #4, transcript:359459 #12
- q59 (Recall@10 0.00): transcript:367133 #25, transcript:374897 nicht gefunden
