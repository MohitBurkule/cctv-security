"""Run the metric checks against real MOTChallenge sequences, when present.

`test_metric_validation.py` proves the metrics behave as defined on synthetic
tracks that are well separated and unambiguous. Real surveillance footage is
neither. MOT20 is a crowded benchmark — hundreds of heavily overlapping people
per frame — and overlap is exactly where a matcher's weaknesses show: a greedy
assignment invents identity switches that an optimal one does not, and boxes
that overlap at IoU 0.4 make the threshold load-bearing in a way it never is on
separated synthetic tracks.

These tests are skipped when the data is absent, so CI stays download-free.

    ~/data/mot/extracted/MOT20/train/MOT20-*/gt/gt.txt
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cctvsec.eval.motchallenge import (
    add_false_positives,
    drop_fraction,
    find_sequences,
    read_sequence,
    swap_identities,
)
from cctvsec.eval.tracking import evaluate_mot

MOT_ROOT = Path.home() / "data" / "mot" / "extracted"

pytestmark = pytest.mark.skipif(
    not list(MOT_ROOT.rglob("gt/gt.txt")) if MOT_ROOT.is_dir() else True,
    reason="MOTChallenge data not downloaded",
)


@pytest.fixture(scope="module")
def sequence():
    """One real sequence, truncated to keep the tests quick.

    Truncation is by frame, never by row: cutting rows mid-frame would remove
    people from frames that still contain their neighbours and manufacture
    misses that the tracker never made.
    """
    seq_dirs = find_sequences(MOT_ROOT)
    if not seq_dirs:
        pytest.skip("no sequences found")
    seq = read_sequence(seq_dirs[0])
    rows = [r for r in seq.gt if r["frame"] < 60]
    if not rows:
        pytest.skip("sequence had no scorable rows")
    return seq.name, rows


def test_real_ground_truth_parses_into_plausible_tracks(sequence) -> None:
    name, rows = sequence
    ids = {r["id"] for r in rows}
    frames = {r["frame"] for r in rows}

    assert len(ids) > 5, f"{name}: expected many people in a crowded scene"
    assert len(frames) == 60
    for r in rows[:200]:
        _x, _y, w, h = r["bbox"]
        assert w > 0 and h > 0, "degenerate box in ground truth"


def test_real_crowded_frames_are_actually_crowded(sequence) -> None:
    """If this fails the file parsed but we are not testing what we think."""
    _, rows = sequence
    per_frame = {}
    for r in rows:
        per_frame[r["frame"]] = per_frame.get(r["frame"], 0) + 1
    assert max(per_frame.values()) > 10


def test_perfect_tracking_on_real_data_scores_perfectly(sequence) -> None:
    """Overlapping bodies must not cost anything when the answer is exact.

    This is the test that catches a greedy matcher. On synthetic separated
    tracks greedy and optimal agree; in a crowd, greedy assignment mismatches
    overlapping pairs and invents identity switches out of nothing.
    """
    _, rows = sequence
    r = evaluate_mot(rows, rows)

    assert r.mota == pytest.approx(1.0, abs=1e-9)
    assert r.idf1 == pytest.approx(1.0, abs=1e-9)
    assert r.id_switches == 0, "optimal matching should invent no switches"
    assert r.false_positives == 0 and r.misses == 0


@pytest.mark.parametrize("fraction", [0.1, 0.3])
def test_mota_on_real_data_still_follows_its_definition(sequence, fraction) -> None:
    _, rows = sequence
    pred = drop_fraction(rows, fraction, seed=11)
    r = evaluate_mot(rows, pred)

    dropped = len(rows) - len(pred)
    assert r.misses == dropped
    assert r.mota == pytest.approx(1.0 - dropped / len(rows), abs=1e-6)


def test_false_positives_on_real_data_cost_what_they_should(sequence) -> None:
    _, rows = sequence
    r = evaluate_mot(rows, add_false_positives(rows, 50, seed=12))
    assert r.false_positives == 50
    assert r.mota == pytest.approx(1.0 - 50 / len(rows), abs=1e-6)


def test_identity_swap_in_a_crowd_hurts_association_not_detection(sequence) -> None:
    """The MTMC failure mode, reproduced on footage where it actually happens."""
    _, rows = sequence
    ids = sorted({r["id"] for r in rows})
    a, b = ids[0], ids[1]
    r = evaluate_mot(rows, swap_identities(rows, a, b, at_frame=30))

    assert r.misses == 0 and r.false_positives == 0
    assert r.mota > 0.99
    assert r.assa <= r.deta


def test_metrics_stay_in_range_on_real_data(sequence) -> None:
    _, rows = sequence
    pred = add_false_positives(drop_fraction(rows, 0.2, seed=13), 30, seed=13)
    r = evaluate_mot(rows, pred)

    for name in ("idf1", "idp", "idr", "hota", "deta", "assa", "motp"):
        assert 0.0 <= getattr(r, name) <= 1.0, f"{name} out of range"
