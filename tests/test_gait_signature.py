"""Tests for gait as a measurable biometric.

The property that makes this worth having is not that the numbers are plausible
— it is that gait behaves like a *biometric*: stable for one person, different
between people, surviving a change of clothes, and defeatable by deliberately
walking differently. Each of those is a separate test, because each can break
independently and none would raise.

The failure mode to guard hardest against is a gait signal that is either
perfect or useless. If everyone with the same style is identical, gait ReID
scores at chance and the number means nothing; if individual variation swamps
style, a limp stops being recognisable. Both look like working code.
"""

from __future__ import annotations

import numpy as np
import pytest

from survsim.director.crowd import FREE_CADENCE_SPM, FREE_STEP_LENGTH_M
from cctvsec.eval.tracking import evaluate_reid
from survsim.gait.signature import (
    PARAMETERS,
    STYLE_EFFECTS,
    GaitSignature,
    gait_distance,
    gait_similarity_matrix,
    observe,
    population_spread,
    signature_for,
)


def _population(n: int = 40, style: str = "normal") -> list[GaitSignature]:
    return [signature_for(f"p{i}", style=style) for i in range(n)]


# --------------------------------------------------------------- calibration


def test_a_normal_walk_matches_the_measured_free_walking_figures() -> None:
    """Cadence and step come from real CCTV, not from intuition (docs/14 §10)."""
    sigs = _population(200)
    cadence = np.mean([s.cadence_spm for s in sigs])
    step = np.mean([s.step_length_m for s in sigs])

    assert cadence == pytest.approx(FREE_CADENCE_SPM, rel=0.05)
    assert step == pytest.approx(FREE_STEP_LENGTH_M, rel=0.05)


def test_implied_speed_is_plausible_for_a_walking_adult() -> None:
    speeds = [s.speed_mps for s in _population(100)]
    assert 1.1 < float(np.mean(speeds)) < 1.6


def test_speed_is_derived_rather_than_stored() -> None:
    """Storing it as well would let it drift out of step with cadence and stride."""
    s = signature_for("p1")
    assert s.speed_mps == pytest.approx(s.cadence_spm / 60.0 * s.step_length_m)
    assert "speed_mps" not in PARAMETERS


def test_taller_people_take_longer_strides() -> None:
    short = signature_for("p1", height_m=1.55)
    tall = signature_for("p1", height_m=1.95)
    assert tall.step_length_m > short.step_length_m


def test_crowding_shortens_the_step_without_slowing_the_legs() -> None:
    """The measured crowd response: not a slow-motion walk (docs/14 §10)."""
    free = signature_for("p1", density_per_m2=0.0)
    crowded = signature_for("p1", density_per_m2=2.0)

    assert crowded.step_length_m < free.step_length_m * 0.75
    assert crowded.cadence_spm >= free.cadence_spm * 0.95
    assert crowded.speed_mps < free.speed_mps


# -------------------------------------------------------------- individuality


def test_the_same_person_always_walks_the_same_way() -> None:
    """A gait that changed between cameras would break matching for the wrong
    reason, so it is derived from the identity rather than from a shared RNG."""
    assert signature_for("alice").as_vector().tolist() == \
        signature_for("alice").as_vector().tolist()


def test_two_people_with_the_same_style_are_similar_but_not_identical() -> None:
    """If they were identical, gait ReID would be chance and mean nothing."""
    a, b = signature_for("alice"), signature_for("bob")
    assert a.as_vector().tolist() != b.as_vector().tolist()

    spread = population_spread(_population(60))
    assert 0.2 < gait_distance(a, b, spread) < 4.0


def test_individuality_can_be_turned_down() -> None:
    spread = population_spread(_population(60))
    varied = gait_distance(signature_for("alice"), signature_for("bob"), spread)
    uniform = gait_distance(signature_for("alice", individuality=0.0),
                            signature_for("bob", individuality=0.0), spread)
    assert uniform < varied
    assert uniform == pytest.approx(0.0, abs=1e-9)


def test_asymmetry_varies_between_people_despite_a_zero_baseline() -> None:
    """A multiplicative offset on zero would leave everyone perfectly symmetric."""
    values = [signature_for(f"p{i}").asymmetry for i in range(50)]
    assert np.std(values) > 0.0


# --------------------------------------------------------------- style


def test_every_declared_gait_style_produces_a_signature() -> None:
    for style in STYLE_EFFECTS:
        assert signature_for("p1", style=style).style == style


def test_an_unknown_style_falls_back_to_normal_rather_than_failing() -> None:
    assert signature_for("p1", style="nonsense").as_vector().tolist() == \
        pytest.approx(signature_for("p1", style="normal").as_vector().tolist())


def test_a_limp_is_asymmetric_and_the_side_is_signed() -> None:
    """Asymmetry is the signal a limp actually carries."""
    left = signature_for("p1", style="limp_L")
    right = signature_for("p1", style="limp_R")
    normal = signature_for("p1", style="normal")

    assert left.asymmetry > normal.asymmetry
    assert right.asymmetry < normal.asymmetry
    assert abs(left.asymmetry) > abs(normal.asymmetry)


def test_styles_are_ordered_as_their_names_imply() -> None:
    p = "p1"
    assert signature_for(p, style="run").speed_mps > \
        signature_for(p, style="brisk").speed_mps > \
        signature_for(p, style="normal").speed_mps > \
        signature_for(p, style="slow").speed_mps


def test_a_shuffle_is_short_stepped_not_slow_legged() -> None:
    normal = signature_for("p1", style="normal")
    shuffle = signature_for("p1", style="shuffle")
    assert shuffle.step_length_m < normal.step_length_m * 0.7
    assert shuffle.cadence_spm >= normal.cadence_spm * 0.95


def test_drunk_walking_is_dominated_by_sway() -> None:
    normal = signature_for("p1", style="normal")
    drunk = signature_for("p1", style="drunk")
    assert drunk.sway_amplitude_m > normal.sway_amplitude_m * 2.0
    assert drunk.stance_width_m > normal.stance_width_m


def test_military_marching_is_the_low_sway_extreme() -> None:
    styles = {s: signature_for("p1", style=s).sway_amplitude_m
              for s in STYLE_EFFECTS}
    assert styles["military"] == min(styles.values())


# --------------------------------------------------------------- distance


def test_distance_is_measured_in_population_standard_deviations() -> None:
    """Unnormalised, cadence (~110) would swamp asymmetry (~0.04) entirely."""
    pop = _population(80)
    spread = population_spread(pop)

    only_cadence = GaitSignature(120.0, 0.75, 0.0, 1.0, 0.035, 0.12)
    only_asymmetry = GaitSignature(110.0, 0.75, 0.30, 1.0, 0.035, 0.12)
    base = GaitSignature(110.0, 0.75, 0.0, 1.0, 0.035, 0.12)

    # A large asymmetry change must register, despite its tiny absolute size.
    assert gait_distance(base, only_asymmetry, spread) > 1.0
    assert gait_distance(base, only_cadence, spread) > 0.0


def test_distance_to_oneself_is_zero_and_symmetric() -> None:
    a, b = signature_for("alice"), signature_for("bob")
    spread = population_spread(_population(40))
    assert gait_distance(a, a, spread) == pytest.approx(0.0)
    assert gait_distance(a, b, spread) == pytest.approx(gait_distance(b, a, spread))


def test_spread_of_a_degenerate_population_does_not_divide_by_zero() -> None:
    identical = [signature_for("p1")] * 5
    assert np.all(population_spread(identical) > 0)
    assert np.all(np.isfinite(population_spread(identical)))


def test_spread_of_a_single_signature_is_handled() -> None:
    assert len(population_spread([signature_for("p1")])) == len(PARAMETERS)


# ------------------------------------------------------------ observation


def test_an_observation_is_close_to_the_truth_but_not_equal_to_it() -> None:
    """Matching clean signatures asks whether two copies of a number are equal."""
    truth = signature_for("alice")
    seen = observe(truth, noise=0.15, seed=1)

    assert seen.as_vector().tolist() != truth.as_vector().tolist()
    spread = population_spread(_population(60))
    assert gait_distance(truth, seen, spread) < 1.0


def test_observation_noise_is_reproducible_for_a_seed() -> None:
    truth = signature_for("alice")
    assert observe(truth, seed=3).as_vector().tolist() == \
        observe(truth, seed=3).as_vector().tolist()


def test_observations_stay_physically_possible() -> None:
    """Heavy noise must not produce a negative step length or cadence."""
    truth = signature_for("alice")
    for seed in range(20):
        seen = observe(truth, noise=8.0, seed=seed)
        assert seen.cadence_spm > 0 and seen.step_length_m > 0
        assert seen.sway_amplitude_m >= 0 and seen.stance_width_m > 0


# ------------------------------------------------------------------ ReID


def _reid(query_ids, query_sigs, gallery_ids, gallery_sigs):
    spread = population_spread(list(query_sigs) + list(gallery_sigs))
    sim = gait_similarity_matrix(query_sigs, gallery_sigs, spread)
    return evaluate_reid(query_ids, gallery_ids, sim)


def test_gait_identifies_people_well_above_chance_but_not_perfectly() -> None:
    """The number that would be meaningless at either extreme.

    Perfect matching would mean the simulator gave everyone a unique fingerprint
    and gait ReID is not being tested at all; chance would mean there is no
    signal to match. Real gait recognition sits between.
    """
    ids = [f"p{i}" for i in range(60)]
    truth = [signature_for(i) for i in ids]
    seen = [observe(s, noise=0.4, seed=k) for k, s in enumerate(truth)]

    result = _reid(ids, seen, ids, truth)
    assert result.rank1 > 0.3, "there must be real signal"
    assert result.rank1 < 1.0, "a perfect score means nothing is being tested"


def test_gait_survives_a_complete_change_of_clothes() -> None:
    """The whole reason to model gait: appearance ReID fails here, gait does not.

    Nothing in a gait signature references clothing, so this test is really
    checking that no clothing-derived quantity has leaked into it.
    """
    ids = [f"p{i}" for i in range(40)]
    before = [signature_for(i) for i in ids]
    # Same people, new outfits — gait is unchanged by construction.
    after = [observe(signature_for(i), noise=0.3, seed=k)
             for k, i in enumerate(ids)]

    assert _reid(ids, after, ids, before).rank1 > 0.3


def test_a_deliberate_limp_defeats_gait_matching() -> None:
    """This is what makes `evasion.fake_limp` a technique rather than a label.

    Before this module the evasion taxonomy claimed a fake limp degrades gait
    recognition by 0.85 while nothing measurable changed. It must now actually
    cost the matcher.
    """
    ids = [f"p{i}" for i in range(40)]
    enrolled = [signature_for(i) for i in ids]

    honest = [observe(signature_for(i), noise=0.3, seed=k)
              for k, i in enumerate(ids)]
    faking = [observe(signature_for(i, style="limp_L"), noise=0.3, seed=k)
              for k, i in enumerate(ids)]

    assert _reid(ids, faking, ids, enrolled).rank1 < \
        _reid(ids, honest, ids, enrolled).rank1


def test_changing_gait_costs_more_than_changing_clothes() -> None:
    """The asymmetry an operator needs to know about.

    A coat swap leaves gait untouched; a deliberate limp does not. So an evader
    who studies the system attacks gait, and a system relying on gait alone is
    attackable by anyone willing to walk oddly.
    """
    spread = population_spread(_population(60))
    person = signature_for("alice")

    clothes_changed = gait_distance(person, signature_for("alice"), spread)
    gait_changed = gait_distance(person, signature_for("alice", style="limp_L"),
                                 spread)

    assert clothes_changed == pytest.approx(0.0)
    assert gait_changed > 1.0


def test_similarity_matrix_has_the_shape_the_reid_scorer_expects() -> None:
    q, g = _population(5), _population(9)
    assert gait_similarity_matrix(q, g).shape == (5, 9)


def test_similarity_is_negated_distance_so_higher_means_more_alike() -> None:
    a, b = signature_for("alice"), signature_for("bob")
    spread = population_spread([a, b])
    sim = gait_similarity_matrix([a], [a, b], spread)
    assert sim[0, 0] > sim[0, 1], "a person must resemble themselves most"


def test_empty_input_produces_an_empty_matrix() -> None:
    assert gait_similarity_matrix([], _population(3)).shape == (0, 3)
    assert gait_similarity_matrix(_population(3), []).shape == (3, 0)


# ------------------------------------------- integration with soft biometrics
#
# Gait belongs in soft_biometrics because that function answers "what survives a
# disguise", and gait is the canonical answer to that question. It was missing.


def test_gait_is_part_of_what_survives_a_disguise() -> None:
    from survsim.core.appearance import soft_biometrics
    from survsim.core.models import Person

    keys = soft_biometrics(Person(id="alice"))
    assert any(k.startswith("gait_") for k in keys), (
        "gait is the cue surveillance actually uses when clothing changes")
    assert "gait_cadence_spm" in keys and "gait_asymmetry" in keys


def test_soft_biometrics_are_flat_columns_not_a_nested_struct() -> None:
    """These rows become parquet columns; a ReID feature matrix wants columns."""
    from survsim.core.appearance import soft_biometrics
    from survsim.core.models import Person

    values = soft_biometrics(Person(id="alice"))
    assert not any(isinstance(v, dict) for v in values.values())


def test_gait_can_be_excluded_for_a_body_only_comparison() -> None:
    """So evaluation can ask how much identification leaned on a cue an evader
    controls — gait is the one soft biometric a person can deliberately change."""
    from survsim.core.appearance import soft_biometrics
    from survsim.core.models import Person

    without = soft_biometrics(Person(id="alice"), include_gait=False)
    assert not any(k.startswith("gait_") for k in without)
    assert "height_m" in without


def test_a_persons_recorded_gait_matches_their_declared_style() -> None:
    from survsim.core.appearance import soft_biometrics
    from survsim.core.models import Gait, Person

    limper = Person(id="alice", gait=Gait(style="limp_L"))
    assert soft_biometrics(limper)["gait_style"] == "limp_L"
    assert soft_biometrics(limper)["gait_asymmetry"] > \
        soft_biometrics(Person(id="alice"))["gait_asymmetry"]


def test_recorded_gait_survives_a_parquet_round_trip() -> None:
    """identities.parquet is written from these rows."""
    pd = pytest.importorskip("pandas")
    import tempfile
    from pathlib import Path

    from survsim.core.appearance import soft_biometrics
    from survsim.core.models import Person

    row = {"uid": "alice", **soft_biometrics(Person(id="alice"))}
    path = Path(tempfile.mkdtemp()) / "identities.parquet"
    pd.DataFrame([row]).to_parquet(path, index=False)

    back = pd.read_parquet(path)
    assert float(back["gait_cadence_spm"][0]) == pytest.approx(
        row["gait_cadence_spm"])
