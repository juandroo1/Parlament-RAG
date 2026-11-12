# OData-Fixtures

Echte, unveränderte Antworten von `https://ws.parlament.ch/odata.svc/`, abgerufen am 2026-11-12 in Task 0.2. Tests laufen nur gegen diese Dateien, nie gegen die Live-API. Die Erkenntnisse daraus stehen in `specs/001-frag-das-parlament/plan.md`, Abschnitt 3.

Beispiel: Herbstsession 2026 (Session 5215), Ständerat am 15.09.2026 (Meeting 5262), Traktandum 82315 (drei PFAS-Motionen).

| Datei | Request (relativ zum Endpunkt) | Zweck |
|---|---|---|
| `metadata.xml` | `$metadata` | Schema-Referenz aller Entitäten |
| `session_legislature52_de.json` | `Session?$filter=LegislativePeriodNumber eq 52 and Language eq 'DE'&$orderby=StartDate desc&$format=json` | Sessions der 52. Legislatur |
| `subject_meeting5262_de.json` | `Subject?$filter=IdMeeting eq 5262 and Language eq 'DE'&$expand=SubjectsBusiness&$orderby=SortOrder&$format=json` | Traktanden einer Sitzung mit verknüpften Geschäften |
| `transcript_subject82315_de.json` | `Transcript?$filter=IdSubject eq 82315 and Language eq 'DE'&$orderby=SortOrder&$format=json` | Voten eines Traktandums, deutsche Sprachzeile |
| `transcript_subject82315_fr.json` | wie oben mit `Language eq 'FR'` | dieselben Voten, französische Sprachzeile (Duplikat-Nachweis) |
| `business_20253906_de.json` | `Business?$filter=ID eq 20253906 and Language eq 'DE'&$format=json` | Motion 25.3906, deutsche Fassung |
| `business_20253906_fr.json` | wie oben mit `Language eq 'FR'` | Motion 25.3906, französische Fassung |

Neue Fixtures nur mit Eintrag in dieser Tabelle hinzufügen.
