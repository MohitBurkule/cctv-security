"""Tests for RF, audio and sensor fusion.

The assertions encode the field realities that make these channels useful or
useless: MAC randomisation over-counts, RSSI cannot localise, quiet-site audio
thresholds fail in crowds, and AND-gating only helps when nuisances really are
independent.
"""

from __future__ import annotations

import numpy as np
import pytest

from cctvsec.eval.fusion import (
    SensorChannel,
    associate_rf_to_tracks,
    fuse,
    independence_penalty,
)
from survsim.sensors.audio import (
    AudioConfig,
    AudioSimulator,
    Microphone,
    ambient_level,
    spl_at,
)
from survsim.sensors.rf import (
    Emitter,
    RfConfig,
    RfSimulator,
    Sniffer,
    distance_from_rssi,
    rssi_at,
)

# --------------------------------------------------------------------- RF


def test_rssi_falls_with_distance() -> None:
    cfg, rng = RfConfig(shadowing_sigma_db=0.0), np.random.default_rng(0)
    near = rssi_at(2.0, 15.0, cfg, rng)
    far = rssi_at(40.0, 15.0, cfg, rng)
    assert near > far


def test_distance_from_rssi_inverts_the_model() -> None:
    cfg, rng = RfConfig(shadowing_sigma_db=0.0), np.random.default_rng(0)
    for d in (2.0, 10.0, 35.0):
        assert distance_from_rssi(rssi_at(d, 15.0, cfg, rng), cfg) == pytest.approx(d, rel=1e-6)


def test_mac_randomisation_rotates_over_time() -> None:
    e = Emitter(uid="p1", randomise_mac=True, rotate_every_s=60.0)
    rng = np.random.default_rng(0)
    assert e.mac_at(10.0, rng) == e.mac_at(50.0, rng)      # same window
    assert e.mac_at(10.0, rng) != e.mac_at(130.0, rng)     # later window


def test_randomised_macs_set_the_locally_administered_bit() -> None:
    """Randomised addresses carry a signature that they are not real hardware."""
    mac = Emitter(uid="p1", randomise_mac=True).mac_at(0.0, np.random.default_rng(0))
    assert int(mac.split(":")[0], 16) & 0x02


def test_mac_randomisation_inflates_a_naive_headcount() -> None:
    """One MAC does not equal one person — a counter that assumes so over-counts."""
    sniffers = [Sniffer(id="s1", pos=(0.0, 0.0, 3.0))]
    emitters = [Emitter(uid=f"p{i}", interval_s=5.0, rotate_every_s=30.0) for i in range(4)]
    sim = RfSimulator(sniffers, emitters, RfConfig(detection_jitter=0.0), seed=1)

    for tick in range(600):
        t = tick * 1.0
        sim.step(t, {f"p{i}": np.array([2.0 + i, 1.0]) for i in range(4)})

    assert sim.true_person_count() == 4
    assert sim.naive_device_count() > 4
    assert sim.overcount_ratio() > 2.0


def test_disabling_randomisation_gives_an_accurate_count() -> None:
    sniffers = [Sniffer(id="s1", pos=(0.0, 0.0, 3.0))]
    emitters = [Emitter(uid=f"p{i}", interval_s=5.0, randomise_mac=False) for i in range(3)]
    sim = RfSimulator(sniffers, emitters, RfConfig(detection_jitter=0.0), seed=2)
    for tick in range(60):
        sim.step(tick * 1.0, {f"p{i}": np.array([3.0, float(i)]) for i in range(3)})
    assert sim.overcount_ratio() == pytest.approx(1.0)


def test_rssi_localisation_carries_metres_of_error() -> None:
    """Shadowing means RSSI cannot pinpoint anyone; it can only corroborate."""
    sniffers = [Sniffer(id="s1", pos=(0.0, 0.0, 3.0))]
    emitters = [Emitter(uid="p0", interval_s=1.0)]
    sim = RfSimulator(sniffers, emitters, RfConfig(detection_jitter=0.0), seed=3)
    for tick in range(200):
        sim.step(tick * 1.0, {"p0": np.array([15.0, 0.0])})
    assert sim.localisation_error()["mean_abs_error_m"] > 1.0


def test_out_of_range_emitters_are_not_heard() -> None:
    sniffers = [Sniffer(id="s1", pos=(0.0, 0.0, 3.0), sensitivity_dbm=-60.0)]
    sim = RfSimulator(sniffers, [Emitter(uid="p0", interval_s=1.0)],
                      RfConfig(shadowing_sigma_db=0.0, detection_jitter=0.0), seed=4)
    sim.step(0.0, {"p0": np.array([500.0, 0.0])})
    assert sim.detections == []


# ------------------------------------------------------------------ audio


def test_spl_follows_inverse_square() -> None:
    """Doubling the distance costs ~6 dB."""
    assert spl_at(10.0, 90.0) - spl_at(20.0, 90.0) == pytest.approx(6.0, abs=0.6)


def test_ambient_rises_with_crowd_size() -> None:
    cfg = AudioConfig()
    assert ambient_level(cfg, 64) > ambient_level(cfg, 2)


def test_a_threshold_tuned_when_quiet_fails_in_a_crowd() -> None:
    """The reason acoustic detectors regress from pilot to deployment."""
    mics = [Microphone(id="m1", pos=(0.0, 0.0, 4.0))]
    quiet = AudioSimulator(mics, AudioConfig(), seed=0)
    assert quiet.emit(0.0, "raised_voice", np.array([20.0, 0.0]), crowd_size=1)

    busy = AudioSimulator(mics, AudioConfig(), seed=0)
    assert busy.emit(0.0, "raised_voice", np.array([20.0, 0.0]), crowd_size=256) == []


def test_loud_events_still_carry_in_a_crowd() -> None:
    mics = [Microphone(id="m1", pos=(0.0, 0.0, 4.0))]
    sim = AudioSimulator(mics, AudioConfig(), seed=0)
    assert sim.emit(0.0, "gunshot", np.array([25.0, 0.0]), crowd_size=256)


def test_doa_error_grows_as_signal_weakens() -> None:
    mics = [Microphone(id="m1", pos=(0.0, 0.0, 4.0))]
    near = AudioSimulator(mics, AudioConfig(), seed=5)
    far = AudioSimulator(mics, AudioConfig(), seed=5)
    for _ in range(80):
        near.emit(0.0, "glass_break", np.array([5.0, 3.0]))
        far.emit(0.0, "glass_break", np.array([60.0, 35.0]))
    assert far.doa_error_stats()["mean_abs_deg"] > near.doa_error_stats()["mean_abs_deg"]


def test_nuisance_sounds_destroy_precision_of_a_trusting_system() -> None:
    """Fireworks and dropped bottles are why raw acoustic alarms are not usable."""
    mics = [Microphone(id="m1", pos=(0.0, 0.0, 4.0))]
    sim = AudioSimulator(mics, AudioConfig(), seed=6)
    sim.emit(0.0, "glass_break", np.array([8.0, 0.0]))
    for i in range(9):
        sim.emit_nuisance(float(i + 1), "glass_break", np.array([7.0, 1.0]))
    assert sim.precision_if_all_detections_alarmed() < 0.3


# ----------------------------------------------------------------- fusion


def _channels() -> list[SensorChannel]:
    return [SensorChannel("camera", p_detect=0.9, false_alarms_per_hour=0.5),
            SensorChannel("rf", p_detect=0.8, false_alarms_per_hour=1.0)]


def test_and_gate_cuts_false_alarms_when_nuisance_is_independent() -> None:
    result = fuse(_channels(), "and", window_s=10.0, correlation=0.0)
    assert result.false_alarms_per_hour < 0.5       # better than either channel
    assert result.p_detect == pytest.approx(0.72)   # but detection is the product


def test_or_gate_adds_false_alarms() -> None:
    result = fuse(_channels(), "or")
    assert result.false_alarms_per_hour == pytest.approx(1.5)
    assert result.p_detect > 0.9


def test_correlated_nuisance_destroys_the_fusion_benefit() -> None:
    """Wind, rain and vehicles trip both sensors; the AND gate then buys nothing."""
    independent = fuse(_channels(), "and", correlation=0.0)
    correlated = fuse(_channels(), "and", correlation=0.9)

    assert correlated.false_alarms_per_hour > 10 * independent.false_alarms_per_hour
    assert any("verify independence" in n for n in correlated.notes)


def test_independence_penalty_quantifies_the_lost_gain() -> None:
    clean = independence_penalty(_channels(), correlation=0.0)
    dirty = independence_penalty(_channels(), correlation=0.8)
    assert clean["gain_realised_fraction"] > 0.95
    assert dirty["gain_realised_fraction"] < 0.5


def test_and_gate_always_costs_detection() -> None:
    result = fuse(_channels(), "and")
    assert result.p_detect < min(c.p_detect for c in _channels())
    assert any("costs detection" in n for n in result.notes)


# ------------------------------------------------------------ association


def test_rf_macs_associate_to_the_right_visual_tracks() -> None:
    sniffers = [Sniffer(id="s1", pos=(0.0, 0.0, 3.0)), Sniffer(id="s2", pos=(40.0, 0.0, 3.0))]
    positions = {"p0": np.array([5.0, 0.0]), "p1": np.array([35.0, 0.0])}
    emitters = [Emitter(uid="p0", interval_s=1.0, randomise_mac=False),
                Emitter(uid="p1", interval_s=1.0, randomise_mac=False)]
    sim = RfSimulator(sniffers, emitters, RfConfig(shadowing_sigma_db=1.0,
                                                   detection_jitter=0.0), seed=7)
    for tick in range(60):
        sim.step(tick * 1.0, positions)

    result = associate_rf_to_tracks(
        sim.detections, positions,
        {"s1": np.array([0.0, 0.0]), "s2": np.array([40.0, 0.0])}, max_error_m=8.0)
    assert result["n_scored"] == 2
    assert result["accuracy"] == pytest.approx(1.0)
