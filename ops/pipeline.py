"""Weekly program review: KPIs, delivery forecast, RAG status and actions."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
FORECAST_WEEKS = 3          # incoming batches assumed at the contracted weekly cadence
MARGIN_AMBER = 0.15
RAG_ORDER = {"Green": 0, "Amber": 1, "Red": 2}


@dataclass
class Status:
    workstream_id: str
    name: str
    delivery: str
    quality: str
    margin: str
    overall: str
    notes: list[str]
    actions: list[str]


def load(con, data_dir: Path) -> None:
    for table in ["dim_workstream", "dim_annotator", "dim_batch", "fact_production", "fact_timesheet", "fact_incident"]:
        con.execute(f"CREATE OR REPLACE TABLE {table} AS SELECT * FROM read_csv_auto('{data_dir / table}.csv')")
    con.execute((ROOT / "sql" / "views.sql").read_text())


def forecast_batches(batches: pd.DataFrame, daily_capacity: float, start: pd.Timestamp) -> pd.DataFrame:
    """Burn open batches oldest-first at a constant daily capacity; return projected finish dates."""
    rows = []
    day = start
    left_today = daily_capacity
    for b in batches.sort_values("received_date").itertuples(index=False):
        remaining = b.remaining_units
        day = max(day, pd.Timestamp(b.received_date))
        while day.weekday() >= 5:
            day += pd.Timedelta(days=1)
        while remaining > 1e-6:
            used = min(left_today, remaining)
            remaining -= used
            left_today -= used
            if remaining > 1e-6:
                day = (day + pd.offsets.BDay(1)).normalize()
                left_today = daily_capacity
        rows.append({**b._asdict(), "projected_finish": day, "slack_days": (pd.Timestamp(b.due_date) - day).days})
    return pd.DataFrame(rows)


def daily_capacity(cap: pd.Series, headcount: int) -> float:
    return cap["recent_uph"] * cap["productive_hours_per_day"] * cap["attendance"] * headcount


def required_headcount(batches, cap, start, current: int) -> int:
    """Smallest headcount that delivers every open and incoming batch on time."""
    for headcount in range(max(current, 1), current + 15):
        fc = forecast_batches(batches, daily_capacity(cap, headcount), start)
        if (fc["slack_days"] >= 0).all():
            return headcount
    return current + 15


def rag(value: float, amber: float, red: float, higher_is_better: bool = True) -> str:
    if not higher_is_better:
        value, amber, red = -value, -amber, -red
    if value < red:
        return "Red"
    if value < amber:
        return "Amber"
    return "Green"


def run(data_dir: Path = ROOT / "data", out_dir: Path = ROOT) -> dict:
    con = duckdb.connect()
    load(con, data_dir)

    as_of = pd.Timestamp(con.execute("SELECT MAX(date) FROM fact_timesheet").fetchone()[0])
    start = (as_of + pd.offsets.BDay(1)).normalize()
    workstreams = con.execute("SELECT * FROM dim_workstream ORDER BY workstream_id").df()
    weekly = con.execute("SELECT * FROM v_weekly_kpis ORDER BY workstream_id, week").df()
    batches = con.execute("SELECT * FROM v_batch_status ORDER BY batch_id").df()
    capacity = con.execute("SELECT * FROM v_recent_capacity").df().set_index("workstream_id")
    incidents = con.execute("SELECT * FROM fact_incident ORDER BY date").df()
    last_week = int(weekly["week"].max())
    recent = weekly[weekly["week"] > last_week - 4]

    statuses, forecasts = [], []
    for ws in workstreams.itertuples(index=False):
        cap = capacity.loc[ws.workstream_id]
        open_batches = batches[(batches["workstream_id"] == ws.workstream_id) & ~batches["delivered"]]
        last_received = batches.loc[batches["workstream_id"] == ws.workstream_id, "received_date"].max()
        incoming = pd.DataFrame([
            {"batch_id": f"{ws.workstream_id}-next{i}", "workstream_id": ws.workstream_id,
             "received_date": last_received + pd.Timedelta(weeks=i), "due_date": last_received + pd.Timedelta(weeks=i, days=int(ws.sla_days)),
             "units": ws.batch_size, "remaining_units": float(ws.batch_size)}
            for i in range(1, FORECAST_WEEKS + 1)
        ])
        pipeline = pd.concat([open_batches[incoming.columns], incoming], ignore_index=True)
        current = int(cap["active_headcount"])
        fc = forecast_batches(pipeline, daily_capacity(cap, current), start)
        fc["forecast_only"] = fc["batch_id"].str.contains("next")
        forecasts.append(fc)
        needed = required_headcount(pipeline, cap, start, current)

        ws_recent = recent[recent["workstream_id"] == ws.workstream_id]
        quality = (ws_recent["quality"] * ws_recent["units"]).sum() / ws_recent["units"].sum()
        margin = 1 - ws_recent["labor_cost_eur"].sum() / ws_recent["revenue_eur"].sum()
        uph = (ws_recent["uph"] * ws_recent["units"]).sum() / ws_recent["units"].sum()
        min_slack = int(fc["slack_days"].min())

        delivery = "Red" if min_slack < 0 else ("Amber" if min_slack <= 1 else "Green")
        quality_rag = rag(quality, ws.quality_target, ws.quality_target - 0.02)
        margin_rag = rag(margin, MARGIN_AMBER, 0.0)
        overall = max([delivery, quality_rag, margin_rag], key=RAG_ORDER.get)

        notes, actions = [], []
        if delivery != "Green":
            late = fc[fc["slack_days"] < 0]
            first = late.iloc[0] if len(late) else fc.loc[fc["slack_days"].idxmin()]
            notes.append(f"{first['batch_id']} projected {first['projected_finish']:%d %b} vs due {pd.Timestamp(first['due_date']):%d %b} ({first['slack_days']:+d} days)")
        if needed > current:
            actions.append(f"Add {needed - current} trained annotator(s) ({current} -> {needed}) to deliver every batch in the next {FORECAST_WEEKS} weeks on time")
        if uph < ws.target_uph * 0.9:
            notes.append(f"Speed {uph:.1f} UPH vs {ws.target_uph:g} planned ({uph / ws.target_uph - 1:+.0%})")
        if quality_rag != "Green":
            notes.append(f"Quality {quality:.1%} vs {ws.quality_target:.0%} client target")
            actions.append("Calibration round on the top 3 error categories + raise QA sampling to 20% until back on target")
        if margin_rag != "Green":
            notes.append(f"Margin {margin:.0%} over the last 4 weeks (cost {ws_recent['cost_per_unit'].mean():.2f} vs price {ws.price_per_unit:.2f} EUR/unit)")
            actions.append(
                "Review pricing with the client or rebalance staffing toward lower-cost sites" if margin < 0
                else "Check for scope change (e.g. guideline updates) and raise a change request on the unit price"
            )
        statuses.append(Status(ws.workstream_id, ws.name, delivery, quality_rag, margin_rag, overall, notes, actions))

    forecast = pd.concat(forecasts, ignore_index=True)
    delivered = batches[batches["delivered"]]
    totals = weekly.groupby("week")[["units", "labor_cost_eur", "revenue_eur"]].sum().reset_index()
    prog_recent = recent.sum(numeric_only=True)

    summary = {
        "as_of": f"{as_of:%Y-%m-%d}",
        "week": last_week,
        "workstreams": len(workstreams),
        "annotators": int(capacity["active_headcount"].sum()),
        "batches_delivered": int(len(delivered)),
        "on_time_rate": float(delivered["on_time"].mean()),
        "batches_at_risk": int((forecast["slack_days"] < 0).sum()),
        "revenue_4w": float(prog_recent["revenue_eur"]),
        "margin_4w": float(1 - prog_recent["labor_cost_eur"] / prog_recent["revenue_eur"]),
        "quality_4w": float((recent["quality"] * recent["units"]).sum() / recent["units"].sum()),
        "red": sum(s.overall == "Red" for s in statuses),
        "amber": sum(s.overall == "Amber" for s in statuses),
    }

    def records(df):
        return json.loads(df.to_json(orient="records", date_format="iso"))

    result = {
        "summary": summary,
        "status": [asdict(s) for s in statuses],
        "weekly": records(weekly),
        "program_weekly": records(totals),
        "forecast": records(forecast),
        "batches": records(batches),
        "incidents": records(incidents),
    }
    (out_dir / "reports").mkdir(exist_ok=True)
    (out_dir / "reports" / "program_results.json").write_text(json.dumps(result, indent=2))
    return result


if __name__ == "__main__":
    from ops.dashboard import build_dashboard
    from ops.report import write_report

    result = run()
    write_report(result, ROOT / "reports" / f"status_report_week_{result['summary']['week']:02d}.md")
    build_dashboard(result, ROOT / "docs" / "index.html")
    s = result["summary"]
    print(f"Week {s['week']}: {s['red']} red, {s['amber']} amber, {s['batches_at_risk']} batches at risk, on-time {s['on_time_rate']:.0%}")
