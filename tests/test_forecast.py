import pandas as pd

from ops.pipeline import forecast_batches, rag, required_headcount


def batch(batch_id, received, due, remaining):
    return {"batch_id": batch_id, "received_date": pd.Timestamp(received), "due_date": pd.Timestamp(due), "remaining_units": remaining}


def test_forecast_burns_oldest_batch_first():
    batches = pd.DataFrame([batch("B2", "2026-09-07", "2026-09-21", 100), batch("B1", "2026-08-31", "2026-09-14", 100)])
    fc = forecast_batches(batches, daily_capacity=100, start=pd.Timestamp("2026-09-14"))  # Monday
    assert list(fc["batch_id"]) == ["B1", "B2"]
    assert list(fc["projected_finish"]) == [pd.Timestamp("2026-09-14"), pd.Timestamp("2026-09-15")]


def test_forecast_skips_weekends():
    batches = pd.DataFrame([batch("B1", "2026-09-07", "2026-09-30", 250)])
    fc = forecast_batches(batches, daily_capacity=100, start=pd.Timestamp("2026-09-11"))  # Friday
    assert fc["projected_finish"].iloc[0] == pd.Timestamp("2026-09-15")  # Fri, Mon, Tue


def test_future_batch_cannot_start_before_it_arrives():
    batches = pd.DataFrame([batch("B9", "2026-09-21", "2026-10-05", 50)])
    fc = forecast_batches(batches, daily_capacity=100, start=pd.Timestamp("2026-09-14"))
    assert fc["projected_finish"].iloc[0] == pd.Timestamp("2026-09-21")


def test_required_headcount_finds_smallest_team_that_is_on_time():
    batches = pd.DataFrame([batch("B1", "2026-09-14", "2026-09-18", 1000)])  # Mon-Fri = 5 working days
    cap = pd.Series({"recent_uph": 10, "productive_hours_per_day": 5, "attendance": 1.0})  # 50 units / person / day
    # 1,000 units in 5 days needs 200/day -> 4 people
    assert required_headcount(batches, cap, pd.Timestamp("2026-09-14"), current=2) == 4


def test_rag_thresholds():
    assert rag(0.95, amber=0.92, red=0.90) == "Green"
    assert rag(0.91, amber=0.92, red=0.90) == "Amber"
    assert rag(0.89, amber=0.92, red=0.90) == "Red"
