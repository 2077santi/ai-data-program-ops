"""End-to-end: the weekly review must surface the storylines planted in the data."""

import pytest

from ops.generate_data import generate
from ops.pipeline import run


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    root = tmp_path_factory.mktemp("run")
    generate(root / "data")
    return run(data_dir=root / "data", out_dir=root)


def status(result, ws):
    return next(s for s in result["status"] if s["workstream_id"] == ws)


def test_speech_workstream_flagged_late_with_staffing_action(result):
    ws2 = status(result, "WS2")
    assert ws2["delivery"] == "Red"
    assert any("Add" in a and "annotator" in a for a in ws2["actions"])


def test_preference_ranking_flagged_on_quality(result):
    ws4 = status(result, "WS4")
    assert ws4["quality"] == "Red"
    assert ws4["delivery"] == "Green"


def test_image_boxes_flagged_on_margin(result):
    assert status(result, "WS3")["margin"] == "Red"


def test_healthy_workstreams_stay_green(result):
    for ws in ["WS1", "WS5", "WS6"]:
        assert status(result, ws)["overall"] == "Green"


def test_past_delivery_was_on_time_but_forecast_warns(result):
    s = result["summary"]
    assert s["on_time_rate"] == 1.0
    assert s["batches_at_risk"] > 0  # early warning before the miss happens
