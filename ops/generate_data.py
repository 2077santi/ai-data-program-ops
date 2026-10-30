"""Simulate 10 weeks of a multi-workstream AI data program ("Project Atlas").

Output is a small star schema, the grain a delivery team actually reports at:
one row per annotator per day in fact_production, plus batches, timesheets
and incidents. Planted storylines the analysis should surface:
  - WS2 Spanish speech: guideline v2 in week 7 slows work 22%, then two
    annotators leave in week 8 -> the open batches drift toward a late delivery.
  - WS4 LLM preference ranking: quality sits below the 90% client target.
  - WS3 image boxes: throughput below plan, so cost per unit exceeds the price.
  - A labeling-tool outage on 2026-08-19 costs every workstream ~1.5 hours.
"""

from pathlib import Path

import numpy as np
import pandas as pd

SEED = 11
START = pd.Timestamp("2026-07-06")
AS_OF = pd.Timestamp("2026-09-11")
OUTAGE_DAY = pd.Timestamp("2026-08-19")

WORKSTREAMS = pd.DataFrame(
    [
        ("WS1", "Search relevance rating", "judgment", 60, 0.92, 0.26, 19000, 10),
        ("WS2", "Spanish speech transcription", "audio minute", 6.0, 0.95, 4.00, 1500, 14),
        ("WS3", "Image bounding boxes", "image", 25, 0.93, 0.95, 4700, 10),
        ("WS4", "LLM preference ranking", "comparison", 18, 0.90, 1.65, 5100, 10),
        ("WS5", "Safety red-team prompts", "prompt", 8, 0.90, 3.70, 1550, 14),
        ("WS6", "Document OCR QA", "page", 40, 0.96, 0.36, 7800, 10),
    ],
    columns=["workstream_id", "name", "unit", "target_uph", "quality_target", "price_per_unit", "batch_size", "sla_days"],
)

# (site, hourly cost EUR, headcount per workstream)
STAFFING = {
    "WS1": [("Manila", 8.5, 6), ("Bogota", 9.5, 4)],
    "WS2": [("Barcelona", 18.0, 5), ("Bogota", 9.5, 3)],
    "WS3": [("Barcelona", 18.0, 7)],
    "WS4": [("Lisbon", 16.0, 6), ("Barcelona", 18.0, 3)],
    "WS5": [("Barcelona", 18.0, 4), ("Lisbon", 16.0, 2)],
    "WS6": [("Manila", 8.5, 6)],
}
LEAVERS = {"WS2": 2}               # annotators who leave on the first day of week 8
SPEED = {"WS1": 1.02, "WS2": 1.0, "WS3": 0.84, "WS4": 1.0, "WS5": 1.05, "WS6": 1.03}  # actual vs target UPH
QUALITY = {"WS1": 0.945, "WS2": 0.962, "WS3": 0.94, "WS4": 0.872, "WS5": 0.925, "WS6": 0.968}


def _annotators(rng):
    rows = []
    for ws, sites in STAFFING.items():
        for site, cost, n in sites:
            for _ in range(n):
                rows.append((ws, site, cost))
    df = pd.DataFrame(rows, columns=["workstream_id", "site", "hourly_cost_eur"])
    df.insert(0, "annotator_id", [f"AN{i:03d}" for i in range(1, len(df) + 1)])
    df["skill"] = rng.normal(1.0, 0.07, len(df)).clip(0.85, 1.15).round(3)
    df["end_date"] = pd.NaT
    week8 = START + pd.Timedelta(weeks=7)
    for ws, n in LEAVERS.items():
        leavers = df[df["workstream_id"] == ws].sample(n, random_state=SEED).index
        df.loc[leavers, "end_date"] = week8
    return df


def _batches():
    rows = []
    for ws in WORKSTREAMS.itertuples(index=False):
        received = START
        i = 1
        while received <= AS_OF:
            rows.append((f"{ws.workstream_id}-B{i:02d}", ws.workstream_id, received, received + pd.Timedelta(days=ws.sla_days), ws.batch_size))
            received += pd.Timedelta(days=7)
            i += 1
    return pd.DataFrame(rows, columns=["batch_id", "workstream_id", "received_date", "due_date", "units"])


def generate(out_dir: Path, seed: int = SEED) -> None:
    rng = np.random.default_rng(seed)
    out_dir.mkdir(parents=True, exist_ok=True)
    annotators = _annotators(rng)
    batches = _batches()
    ws = WORKSTREAMS.set_index("workstream_id")

    remaining = batches.set_index("batch_id")["units"].astype(float).to_dict()
    production, timesheets, incidents = [], [], []
    for day in pd.bdate_range(START, AS_OF):
        week = (day - START).days // 7 + 1
        if day == OUTAGE_DAY:
            for w in ws.index:
                incidents.append((day, w, "Tool outage", "high", 90, "Labeling tool down 09:40-11:10 (expired certificate)"))
        for a in annotators.itertuples(index=False):
            if pd.notna(a.end_date) and day >= a.end_date:
                continue
            logged = 8.0
            overhead = rng.uniform(0.4, 1.0) + (1.5 if day == OUTAGE_DAY else 0)
            if rng.random() < 0.04:  # sick day / PTO
                timesheets.append((day, a.annotator_id, 0.0, 0.0, "absence"))
                continue
            productive = max(logged - overhead, 0)
            timesheets.append((day, a.annotator_id, logged, round(productive, 2), "worked"))

            uph = ws.at[a.workstream_id, "target_uph"] * SPEED[a.workstream_id] * a.skill * rng.normal(1, 0.06)
            if a.workstream_id == "WS2" and week >= 7:
                uph *= 0.78  # guideline v2: more speaker tags per audio minute
            capacity = uph * productive

            open_batches = [b for b in batches[(batches["workstream_id"] == a.workstream_id) & (batches["received_date"] <= day)]["batch_id"] if remaining[b] > 0]
            for batch_id in open_batches:  # FIFO: oldest open batch first
                if capacity <= 0:
                    break
                units = min(capacity, remaining[batch_id])
                remaining[batch_id] -= units
                capacity -= units
                sampled = max(1, round(units * 0.1))
                passed = rng.binomial(sampled, QUALITY[a.workstream_id])
                production.append((day, a.annotator_id, batch_id, round(units, 1), round(units / uph, 2), sampled, passed))

    incidents.append((pd.Timestamp("2026-08-04"), "WS4", "Guideline clarification", "medium", 45, "Client changed tie-break rule; work paused for Q&A"))
    incidents.append((pd.Timestamp("2026-08-17"), "WS2", "Guideline change", "medium", 60, "Guideline v2: speaker-change tags required"))

    pd.DataFrame(production, columns=["date", "annotator_id", "batch_id", "units", "handle_hours", "qa_sampled", "qa_passed"]).to_csv(out_dir / "fact_production.csv", index=False)
    pd.DataFrame(timesheets, columns=["date", "annotator_id", "logged_hours", "productive_hours", "status"]).to_csv(out_dir / "fact_timesheet.csv", index=False)
    pd.DataFrame(incidents, columns=["date", "workstream_id", "type", "severity", "minutes_lost", "description"]).to_csv(out_dir / "fact_incident.csv", index=False)
    annotators.drop(columns="skill").to_csv(out_dir / "dim_annotator.csv", index=False)
    batches.to_csv(out_dir / "dim_batch.csv", index=False)
    WORKSTREAMS.to_csv(out_dir / "dim_workstream.csv", index=False)
    print(f"Wrote {len(production):,} production rows for {len(annotators)} annotators, {len(batches)} batches -> {out_dir}")


if __name__ == "__main__":
    generate(Path(__file__).resolve().parents[1] / "data")
