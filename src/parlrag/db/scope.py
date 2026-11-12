"""Gemeinsame Abgrenzung «eine Session» für `stats` und `index`.

Die CTE `scope` enthält alle Dokumente, wenn `:session_id` NULL ist; sonst die Voten
dieser Session und die Geschäfte, die im Zeitraum dieser Voten debattiert wurden.
"""

SESSION_SCOPE_CTE = """
WITH session_days AS (
    SELECT min(date) AS first_day, max(date) AS last_day
    FROM documents
    WHERE source_type = 'transcript' AND session_id = CAST(:session_id AS integer)
),
scope AS (
    SELECT d.* FROM documents d
    WHERE CAST(:session_id AS integer) IS NULL
       OR (d.source_type = 'transcript' AND d.session_id = CAST(:session_id AS integer))
       OR (d.source_type = 'business' AND EXISTS (
            SELECT 1 FROM unnest(d.debate_dates) AS debate(day), session_days s
            WHERE debate.day BETWEEN s.first_day AND s.last_day))
)
"""
