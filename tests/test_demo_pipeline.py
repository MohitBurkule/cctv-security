"""Integration test: the whole chain, end to end.

Unit tests prove each module works in isolation; this proves they still work
together. It is the test most likely to catch a change that is locally correct
and globally wrong — an export whose field names drift, a metric that silently
receives an empty set, a generator whose output the simulator can no longer read.
"""

from __future__ import annotations

import json

import pytest

from cctvsec.demo import run_demo

pytestmark = pytest.mark.slow  # one 60 s×2-scene pipeline run shared by the module


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    """One run shared by the module: it exercises the full pipeline and is slow."""
    out = tmp_path_factory.mktemp("demo")
    return run_demo(out, n_scenes=2, duration_s=60.0, fps=5.0, seed=3), out


def test_every_stage_completes(demo) -> None:
    result, _ = demo
    assert result.ok, f"pipeline broke: {result.failures}"
    assert set(result.stages) >= {"generate", "simulate", "coco", "realism",
                                  "behaviour", "alarms"}


def test_generated_scenes_are_valid(demo) -> None:
    result, _ = demo
    assert result.stages["generate"]["invalid"] == []
    assert result.stages["generate"]["all_valid"] is True


def test_simulation_produces_ground_truth_for_many_identities(demo) -> None:
    result, _ = demo
    stage = result.stages["simulate"]
    assert stage["rows"] > 0
    assert stage["identities"] > 5
    assert stage["camera_hours"] > 0


def test_coco_export_reports_difficulty_honestly(demo) -> None:
    """A dataset of people too small to resolve must say so rather than imply mAP."""
    result, out = demo
    stage = result.stages["coco"]
    assert stage["annotations"] > 0
    assert 0.0 <= stage["usable_fraction"] <= 1.0
    assert stage["difficulty"]["height"]

    written = json.loads((out / "coco.json").read_text())
    assert {"images", "annotations", "categories"} <= set(written)


def test_degradation_profiles_score_as_plausible_cctv(demo) -> None:
    result, _ = demo
    for profile, score in result.stages["realism"].items():
        assert score is not None and score > 0.6, f"{profile} scored {score}"


def test_behaviour_model_learns_or_says_why_it_could_not(demo) -> None:
    """At this tiny scale the split may hold no suspicious identities at all.

    docs/14 records that a couple of short scenes cannot support identity-disjoint
    behaviour learning. The contract is therefore not "AUC must be good" but
    "either it learned, or it reported that the evaluation was impossible" — a
    silent 0.5 would look like an honest chance-level result instead.
    """
    result, _ = demo
    stage = result.stages["behaviour"]
    assert stage["segments"] > 0

    if stage["degenerate"]:
        assert stage["degenerate_reason"]
        assert "more scenes" in stage["degenerate_reason"]
    else:
        assert stage["auc"] > 0.5


def test_verification_beats_the_raw_detector(demo) -> None:
    """The headline claim, re-checked on every run rather than asserted once."""
    result, _ = demo
    raw = result.stages["alarms"]["raw"]
    verified = result.stages["alarms"]["verified"]

    assert verified["precision"] >= raw["precision"]
    assert (verified["false_alarms_per_camera_hour"]
            <= raw["false_alarms_per_camera_hour"])


def test_report_is_written_for_inspection(demo) -> None:
    _, out = demo
    report = json.loads((out / "demo_report.json").read_text())
    assert report["ok"] is True
    assert report["stages"]


def test_failures_are_recorded_rather_than_raised(tmp_path) -> None:
    """A broken stage must be reported, not crash the run or pass silently."""
    result = run_demo(tmp_path, n_scenes=1, duration_s=5.0, fps=1.0, seed=0)
    # Whatever happened, the contract holds: ok is consistent with the failure list.
    assert result.ok == (not result.failures)
    assert isinstance(result.as_dict()["failures"], list)
