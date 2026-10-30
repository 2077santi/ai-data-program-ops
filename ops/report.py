"""Write the weekly program status report a Program Analyst sends to the client lead."""

from pathlib import Path

import pandas as pd

DOT = {"Green": "🟢", "Amber": "🟠", "Red": "🔴"}
OWNER = [  # first keyword match decides who owns an action
    ("annotator", "Delivery lead"),
    ("Calibration", "QA lead"),
    ("pricing", "Account manager"),
    ("change request", "Account manager"),
]


def owner(action: str) -> str:
    return next((o for key, o in OWNER if key in action), "Program analyst")


def write_report(result: dict, path: Path) -> None:
    s = result["summary"]
    status = result["status"]
    overall = "Red" if s["red"] else ("Amber" if s["amber"] else "Green")
    weekly = pd.DataFrame(result["weekly"])
    recent = weekly[weekly["week"] > s["week"] - 4]
    forecast = pd.DataFrame(result["forecast"])
    at_risk = forecast[forecast["slack_days"] < 0]

    lines = [
        f"# Program Atlas - Weekly Status Report, Week {s['week']}",
        "",
        f"**As of:** {pd.Timestamp(s['as_of']):%d %b %Y} · **Workstreams:** {s['workstreams']} · **Active annotators:** {s['annotators']}",
        "",
        f"## Overall status: {DOT[overall]} {overall}",
        "",
        f"- **Delivery:** {s['batches_delivered']} batches delivered, **{s['on_time_rate']:.0%} on time** so far. "
        f"Forecast: **{s['batches_at_risk']} upcoming batch(es) will miss their due date** without action.",
        f"- **Quality (last 4 weeks):** {s['quality_4w']:.1%} QA pass rate across the program.",
        f"- **Financials (last 4 weeks):** revenue {s['revenue_4w']:,.0f} EUR, gross margin **{s['margin_4w']:.0%}**.",
        f"- **{s['red']} workstream(s) red, {s['amber']} amber**: details and actions below.",
        "",
        "## Workstream status",
        "",
        "| Workstream | Delivery | Quality | Margin | Overall | What's happening |",
        "|---|:-:|:-:|:-:|:-:|---|",
    ]
    for st in status:
        lines.append(
            f"| **{st['workstream_id']}** {st['name']} | {DOT[st['delivery']]} | {DOT[st['quality']]} | {DOT[st['margin']]} | "
            f"{DOT[st['overall']]} | {'<br>'.join(st['notes']) or 'On track'} |"
        )

    lines += ["", "## Actions", "", "| Workstream | Action | Owner |", "|---|---|---|"]
    for st in status:
        for action in st["actions"]:
            lines.append(f"| {st['workstream_id']} | {action} | {owner(action)} |")

    if len(at_risk):
        lines += ["", "## Delivery forecast: batches at risk", "",
                  "Forecast burns open and incoming batches oldest-first at each team's capacity over the last 2 weeks.", "",
                  "| Batch | Units left | Due | Projected | Slack |", "|---|---:|---|---|---:|"]
        for r in at_risk.itertuples(index=False):
            label = f"{r.batch_id} (expected)" if r.forecast_only else r.batch_id
            lines.append(f"| {label} | {r.remaining_units:,.0f} | {pd.Timestamp(r.due_date):%d %b} | {pd.Timestamp(r.projected_finish):%d %b} | {r.slack_days:+d} days |")

    lines += ["", "## KPIs by workstream (last 4 weeks)", "",
              "| Workstream | Units | UPH (plan) | Quality (target) | Utilization | Cost/unit (price) |", "|---|---:|---:|---:|---:|---:|"]
    for ws_id, g in recent.groupby("workstream_id"):
        units = g["units"].sum()
        lines.append(
            f"| {ws_id} | {units:,.0f} | {(g['uph'] * g['units']).sum() / units:.1f} ({g['target_uph'].iloc[0]:g}) | "
            f"{(g['quality'] * g['units']).sum() / units:.1%} ({g['quality_target'].iloc[0]:.0%}) | {g['utilization'].mean():.0%} | "
            f"{g['labor_cost_eur'].sum() / units:.2f} ({g['price_per_unit'].iloc[0]:.2f}) |"
        )

    lines += ["", "## Incidents this period", "", "| Date | Workstream | Type | Time lost | Description |", "|---|---|---|---:|---|"]
    incidents = pd.DataFrame(result["incidents"])
    for r in incidents.drop_duplicates(["date", "type"]).itertuples(index=False):
        scope = "All" if r.type == "Tool outage" else r.workstream_id
        lines.append(f"| {pd.Timestamp(r.date):%d %b} | {scope} | {r.type} | {r.minutes_lost} min | {r.description} |")

    decisions = [st for st in status if any(owner(a) == "Account manager" for a in st["actions"])]
    if decisions:
        lines += ["", "## Decisions needed from the client", ""]
        for st in decisions:
            lines.append(f"- **{st['workstream_id']} {st['name']}:** {st['notes'][-1]}. Agree a price review or scope change.")
    lines.append("")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines))
