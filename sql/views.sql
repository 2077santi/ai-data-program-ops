-- Program Atlas data model. Tables: dim_workstream, dim_annotator, dim_batch,
-- fact_production, fact_timesheet, fact_incident. Program week 1 starts 2026-07-06.

CREATE OR REPLACE VIEW v_production AS
SELECT
    p.*,
    b.workstream_id,
    a.site,
    a.hourly_cost_eur,
    1 + DATEDIFF('day', DATE '2026-07-06', p.date) // 7 AS week
FROM fact_production p
JOIN dim_batch b USING (batch_id)
JOIN dim_annotator a USING (annotator_id);

-- Paid hours come from timesheets, not from production: idle time is still paid.
CREATE OR REPLACE VIEW v_paid_hours AS
SELECT
    a.workstream_id,
    1 + DATEDIFF('day', DATE '2026-07-06', t.date) // 7 AS week,
    SUM(t.logged_hours) AS logged_hours,
    SUM(t.logged_hours * a.hourly_cost_eur) AS labor_cost_eur,
    COUNT(DISTINCT t.annotator_id) AS headcount
FROM fact_timesheet t
JOIN dim_annotator a USING (annotator_id)
GROUP BY ALL;

-- Weekly KPI cube per workstream: volume, speed, quality, utilization, unit economics.
CREATE OR REPLACE VIEW v_weekly_kpis AS
WITH prod AS (
    SELECT workstream_id, week,
           SUM(units) AS units,
           SUM(handle_hours) AS handle_hours,
           SUM(qa_sampled) AS qa_sampled,
           SUM(qa_passed) AS qa_passed
    FROM v_production
    GROUP BY ALL
)
SELECT
    h.workstream_id,
    h.week,
    h.headcount,
    COALESCE(p.units, 0) AS units,
    p.units / NULLIF(p.handle_hours, 0) AS uph,
    w.target_uph,
    p.qa_passed::DOUBLE / NULLIF(p.qa_sampled, 0) AS quality,
    w.quality_target,
    COALESCE(p.handle_hours, 0) / h.logged_hours AS utilization,
    h.labor_cost_eur,
    COALESCE(p.units, 0) * w.price_per_unit AS revenue_eur,
    h.labor_cost_eur / NULLIF(p.units, 0) AS cost_per_unit,
    w.price_per_unit
FROM v_paid_hours h
JOIN dim_workstream w USING (workstream_id)
LEFT JOIN prod p USING (workstream_id, week);

-- One row per batch: progress, delivery date, on-time flag.
CREATE OR REPLACE VIEW v_batch_status AS
WITH progress AS (
    SELECT batch_id, SUM(units) AS done_units, MAX(date) AS last_work_date
    FROM fact_production
    GROUP BY batch_id
)
SELECT
    b.*,
    COALESCE(p.done_units, 0) AS done_units,
    b.units - COALESCE(p.done_units, 0) AS remaining_units,
    COALESCE(p.done_units, 0) >= b.units - 0.5 AS delivered,
    CASE WHEN COALESCE(p.done_units, 0) >= b.units - 0.5 THEN p.last_work_date END AS delivered_date,
    CASE WHEN COALESCE(p.done_units, 0) >= b.units - 0.5 THEN p.last_work_date <= b.due_date END AS on_time
FROM dim_batch b
LEFT JOIN progress p USING (batch_id);

-- Current capacity per workstream, from the last 10 business days.
CREATE OR REPLACE VIEW v_recent_capacity AS
WITH recent AS (
    SELECT * FROM v_production
    WHERE date > (SELECT MAX(date) FROM fact_production) - INTERVAL 14 DAY
),
hours AS (
    SELECT a.workstream_id,
           AVG(t.productive_hours) FILTER (WHERE t.status = 'worked') AS productive_hours_per_day,
           AVG((t.status = 'worked')::INT) AS attendance
    FROM fact_timesheet t JOIN dim_annotator a USING (annotator_id)
    WHERE t.date > (SELECT MAX(date) FROM fact_timesheet) - INTERVAL 14 DAY
    GROUP BY ALL
)
SELECT
    w.workstream_id,
    SUM(r.units) / SUM(r.handle_hours) AS recent_uph,
    h.productive_hours_per_day,
    h.attendance,
    (SELECT COUNT(*) FROM dim_annotator a
      WHERE a.workstream_id = w.workstream_id
        AND (a.end_date IS NULL OR a.end_date > (SELECT MAX(date) FROM fact_timesheet))) AS active_headcount
FROM dim_workstream w
JOIN recent r USING (workstream_id)
JOIN hours h USING (workstream_id)
GROUP BY w.workstream_id, h.productive_hours_per_day, h.attendance;
