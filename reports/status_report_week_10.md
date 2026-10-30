# Program Atlas - Weekly Status Report, Week 10

**As of:** 11 Sep 2026 · **Workstreams:** 6 · **Active annotators:** 44

## Overall status: 🔴 Red

- **Delivery:** 58 batches delivered, **100% on time** so far. Forecast: **5 upcoming batch(es) will miss their due date** without action.
- **Quality (last 4 weeks):** 94.0% QA pass rate across the program.
- **Financials (last 4 weeks):** revenue 122,529 EUR, gross margin **22%**.
- **3 workstream(s) red, 0 amber**: details and actions below.

## Workstream status

| Workstream | Delivery | Quality | Margin | Overall | What's happening |
|---|:-:|:-:|:-:|:-:|---|
| **WS1** Search relevance rating | 🟢 | 🟢 | 🟢 | 🟢 | On track |
| **WS2** Spanish speech transcription | 🔴 | 🟢 | 🟠 | 🔴 | WS2-B09 projected 15 Sep vs due 14 Sep (-1 days)<br>Speed 4.8 UPH vs 6 planned (-20%)<br>Margin 13% over the last 4 weeks (cost 3.49 vs price 4.00 EUR/unit) |
| **WS3** Image bounding boxes | 🟢 | 🟢 | 🔴 | 🔴 | Speed 20.2 UPH vs 25 planned (-19%)<br>Margin -8% over the last 4 weeks (cost 1.03 vs price 0.95 EUR/unit) |
| **WS4** LLM preference ranking | 🟢 | 🔴 | 🟢 | 🔴 | Quality 87.4% vs 90% client target |
| **WS5** Safety red-team prompts | 🟢 | 🟢 | 🟢 | 🟢 | On track |
| **WS6** Document OCR QA | 🟢 | 🟢 | 🟢 | 🟢 | On track |

## Actions

| Workstream | Action | Owner |
|---|---|---|
| WS2 | Add 4 trained annotator(s) (6 -> 10) to deliver every batch in the next 3 weeks on time | Delivery lead |
| WS2 | Check for scope change (e.g. guideline updates) and raise a change request on the unit price | Account manager |
| WS3 | Review pricing with the client or rebalance staffing toward lower-cost sites | Account manager |
| WS4 | Calibration round on the top 3 error categories + raise QA sampling to 20% until back on target | QA lead |

## Delivery forecast: batches at risk

Forecast burns open and incoming batches oldest-first at each team's capacity over the last 2 weeks.

| Batch | Units left | Due | Projected | Slack |
|---|---:|---|---|---:|
| WS2-B09 | 241 | 14 Sep | 15 Sep | -1 days |
| WS2-B10 | 1,500 | 21 Sep | 24 Sep | -3 days |
| WS2-next1 (expected) | 1,500 | 28 Sep | 06 Oct | -8 days |
| WS2-next2 (expected) | 1,500 | 05 Oct | 16 Oct | -11 days |
| WS2-next3 (expected) | 1,500 | 12 Oct | 28 Oct | -16 days |

## KPIs by workstream (last 4 weeks)

| Workstream | Units | UPH (plan) | Quality (target) | Utilization | Cost/unit (price) |
|---|---:|---:|---:|---:|---:|
| WS1 | 76,000 | 61.9 (60) | 94.3% (92%) | 80% | 0.18 (0.26) |
| WS2 | 4,259 | 4.8 (6) | 97.6% (95%) | 90% | 3.49 (4.00) |
| WS3 | 18,800 | 20.2 (25) | 94.5% (93%) | 87% | 1.03 (0.95) |
| WS4 | 20,400 | 17.4 (18) | 87.4% (90%) | 84% | 1.14 (1.65) |
| WS5 | 6,200 | 8.5 (8) | 93.9% (90%) | 78% | 2.61 (3.70) |
| WS6 | 31,319 | 40.8 (40) | 97.0% (96%) | 83% | 0.25 (0.36) |

## Incidents this period

| Date | Workstream | Type | Time lost | Description |
|---|---|---|---:|---|
| 04 Aug | WS4 | Guideline clarification | 45 min | Client changed tie-break rule; work paused for Q&A |
| 17 Aug | WS2 | Guideline change | 60 min | Guideline v2: speaker-change tags required |
| 19 Aug | All | Tool outage | 90 min | Labeling tool down 09:40-11:10 (expired certificate) |

## Decisions needed from the client

- **WS2 Spanish speech transcription:** Margin 13% over the last 4 weeks (cost 3.49 vs price 4.00 EUR/unit). Agree a price review or scope change.
- **WS3 Image bounding boxes:** Margin -8% over the last 4 weeks (cost 1.03 vs price 0.95 EUR/unit). Agree a price review or scope change.
