# Spec - AI Data Program Ops Dashboard

## Context

A multi-workstream AI data program delivers weekly batches to one client under SLAs. The program analyst prepares a weekly review for the client lead, and today it is assembled by hand from several spreadsheets. It looks backward, so a delivery problem shows up only after a batch is late.

## Users

- **Program manager / client lead**: needs status, risks and decisions in 2 minutes.
- **Delivery lead**: staffing and scheduling.
- **QA lead**: quality actions.
- **Account manager**: pricing and change requests.

## Definitions

- **UPH**: units per production hour = units / handle hours.
- **Utilization** = handle hours / logged (paid) hours.
- **Cost per unit** = paid hours × hourly cost / units. Idle time is included.
- **Gross margin** = 1 - labor cost / revenue.
- **Capacity / day** = recent UPH × productive hours per day × attendance × active headcount (last 10 business days).

## Requirements (EARS format)

### Data model

- **R1.** The system shall model the program as a star schema (workstream, annotator, batch dimensions; production, timesheet, incident facts) and compute all KPIs in SQL views.
- **R2.** The system shall compute cost from timesheet (paid) hours, not production hours.

### Forecast

- **R3.** The system shall project the finish date of every open batch, and of the next 3 batches expected at the contracted weekly cadence, by burning them oldest-first at current capacity on business days.
- **R4.** The system shall not start work on a batch before its received date.
- **R5.** When any projected batch finishes after its due date, the system shall compute the smallest headcount that delivers all projected batches on time and recommend the difference.

### RAG status

- **R6.** Delivery shall be **Red** when any batch has negative slack, **Amber** when the minimum slack is 0-1 days, otherwise **Green**.
- **R7.** Quality shall be **Red** below target - 2 pp, **Amber** below target, otherwise **Green** (4-week, volume-weighted).
- **R8.** Margin shall be **Red** below 0%, **Amber** below 15%, otherwise **Green** (4-week).
- **R9.** Overall status shall be the worst of delivery, quality and margin.

### Reporting

- **R10.** The system shall produce a weekly status report with overall status, per-workstream RAG, actions with an owner, at-risk batches, KPIs, incidents, and decisions needed from the client.
- **R11.** If speed is below 90% of plan, then the system shall state the gap in the workstream notes.

## Acceptance tests

| Req | Test |
|---|---|
| R3 | `test_forecast_burns_oldest_batch_first`, `test_forecast_skips_weekends` |
| R4 | `test_future_batch_cannot_start_before_it_arrives` |
| R5 | `test_required_headcount_finds_smallest_team_that_is_on_time`, `test_speech_workstream_flagged_late_with_staffing_action` |
| R6-R8 | `test_rag_thresholds`, `test_preference_ranking_flagged_on_quality`, `test_image_boxes_flagged_on_margin` |
| R9 | `test_healthy_workstreams_stay_green` |

## Out of scope

Annotator-level scheduling, invoicing, and forecasting of client demand beyond the contracted cadence.
