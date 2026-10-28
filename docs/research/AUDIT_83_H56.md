# AUDIT_83_H56 · PTZ dossier 83 and H56 slew-to-alarm experiment

Audited 2026-09-27 against `out/experiments/h56_ptz_slew/results.json`, `survsim/experiments/ptz_slew.py`,
config `survsim/experiments/configs/h56_ptz_slew.yaml`, pre-registration `c0f0ed2` (32 §H56), results `0f05f04`,
and `docs/research/83_PTZ_AUTOTRACK_AND_HANDOFF.md`. CPU only; no GPU, no editor. The experiment was rerun
twice into the scratchpad (`python -m survsim.experiments.ptz_slew`, and `survsim experiment h56_ptz_slew`
once the runner was registered): the `acquire` and `contention` dicts are **identical** to results.json.

**Score: 84 → 100** (every number matched; six imprecise claims corrected in place; one wrong geometric
explanation removed; one ONVIF claim turned [X]; the runner was not reachable from the CLI and is now registered).

## 1. Numbers recomputed

| claim | recomputed | ok |
|---|---|---|
| H39 1 PTZ ≤ 20 m 0.901 [0.872, 0.936] | 0.9011 [0.8723, 0.9359], n 455 | ✓ |
| H39 1 PTZ 20–30 m 0.802 [0.774, 0.830] | 0.8017 [0.7740, 0.8296], n 600 | ✓ |
| H39 1 PTZ > 30 m 0.727 [0.706, 0.747] | 0.7270 [0.7060, 0.7473], n 1,945 | ✓ |
| exact 1 PTZ 0.967 / 0.958 / 0.978 | 0.9670 / 0.9583 / 0.9779 | ✓ |
| 2 PTZ H39 0.897 / 0.772 / 0.691; exact 0.938 / 0.955 / 0.957 | 0.8967 / 0.7717 / 0.6910; 0.9385 / 0.9550 / 0.9573 | ✓ |
| missed second 0.369 [0.325, 0.406] vs 0.057 [0.043, 0.070] | 0.3691 [0.3251, 0.4060] / 0.0566 [0.0428, 0.0696], 1,184 alarms/arm | ✓ |
| overall contention acquire@3s 0.479 / 0.689 | H39 0.4789 / 0.6892 (exact 0.6123 / 0.9139) | ✓ |
| bins 455 / 600 / 1,945 of 3,000 | 300 alarms × 10 seeds, same targets across arms | ✓ |
| seed-cluster bootstrap over 10 seeds | `seed_boot` resamples the 10 seeds with replacement (2,000, rng seed 56), ratio of sums | ✓ |
| "cut contention misses 6.5×" | 0.3691 / 0.0566 = 6.52 | ✓ |
| "calibration costs 7–25 pts" | 6.6 / 15.7 / 25.1 | ✓ (rounded) |
| verdict not met: far 0.727 > 0.6; near and contention met | `decision` = {near True, far False, missed True, met False} | ✓, but near is point-only (§2) |
| "CPU 8 s" (32) | results.json `wall_seconds` 10.0; reruns 7–10 s | ✗ corrected to wall 10.0 s |

## 2. Imprecise claims corrected (83, 32, and every downstream copy)

1. **"≤ 20 m leg held"** → met on the point estimate only; the seed-cluster CI [0.872, 0.936] spans the 0.9 bar.
2. **2 PTZs: "shorter PTZ range = narrower 6 m frame in angle" (83) / "closer PTZ, same 6 m frame, larger angular
   error" (32)** — wrong as stated: a closer PTZ sees a 6 m frame at a *wider* angle, and a fixed metric error and
   a fixed metric frame both scale as 1/range, so their ratio does not change. The exact arm also drops (0.967 →
   0.938 near). Now "cause untested".
3. **"calibration, not motion, costs 7–25 pts"** — kept, with the reason (same targets, headings and motion in both
   arms; motion alone costs 2–4 pts in the exact arm).
4. **Distance bins** are ground range from the *detecting fixed camera*, not from the PTZ; the per-bin error RMSE
   (0.94 / 1.97 / 2.92 m) is the injected H39 input, by construction. Now stated in 83 and 32.
5. **missed_second ≈ busy share.** Busy-at-arrival 0.382 vs missed 0.369: with an assumed 10 s dwell longer than the
   3 s window, a queued alarm is almost never acquired. The 37 % is therefore a queueing number driven by the
   assumed dwell and FIFO policy, not by optics. Stated in 83, 32, FACTS, 64.
6. **"Far-field misses come from a 6 m frame against ~3 m range error"** (83 reading) was stated as fact; it is the
   working explanation and **stays untested** (now H57). Supporting arithmetic only: at 30 m a 6 m frame is
   ~11° hfov, below 83 §3.1's ~22° budget.
7. **Every PTZ timing labelled an assumption** wherever H56 is quoted (200 °/s, 0.5 s latency, 0.8 s zoom, 6 m
   framing, 10 s dwell, open-loop aim, no occlusion).

## 3. 83's [A] items — fetched

| item | source | result |
|---|---|---|
| generic pan/tilt space normalised [−1, 1] | ONVIF PTZ spec v26.06 §5.7.1.1 (pdftotext) | **[V]** — mandatory for nodes supporting absolute pan/tilt |
| spherical pan/tilt space in degrees exists | same, §5.7.1.2 | **[V]** — optional, defined for ceiling dome |
| GetStatus "IDLE or MOVING" | same, MoveStatus | **[V], refined**: optional; IDLE / MOVING / UNKNOWN |
| Profile S: PTZ optional | onvif.org/profiles/profile-s | **[V]** "for … devices and clients that support such features" |
| Profile T: H.265, PTZ optional | onvif.org/profiles/profile-t | **[V], refined**: H.264/H.265; PTZ control **mandatory for clients**, conditional for devices |
| "Auto-tracking is not standardised in ONVIF" | spec §5.3.6 `MoveAndStartTracking` | **[X]** — the move-then-track hand-off (GeoLocation / preset / PTZVector, optional ObjectID) is standardised; the tracker is vendor-specific |
| Axis Autotracking 2 / tampering | help.axis.com (KB loads, no content); product URLs 404 | stays [A] |
| Bosch Intelligent Tracking | boschsecurity.com → 301 to a life-safety site | stays [A] |
| Hanwha auto-tracking | hanwhavision.com (loads, no detail) | stays [A] |
| Zhou 2003 / Senior 2005 / Del Bimbo 2010 | not fetched | stays [A] |

5 [A] → [V] (two refined), 1 [A] → [X]. New FACTS rows cite the spec and profile pages.

## 4. The 10 Q&As trace to FACTS

Q3 (0.96 / 2.92 m), Q5 (`cam_ptz` 30–35° hfov), Q6 (~120 alarms/h, A1), Q8 (H34 1,440, blur missed) trace to
FACTS rows. Q1 (14 %) and Q10 (runner 12 m at 2 s) are arithmetic on stated assumptions. Q2, Q4, Q7 carry no
numbers. Q9 was wrong on auto-tracking and is rewritten from the fetched spec. No Q quoted an H56 number, so
no Q&A needed the §2 corrections.

## 5. Registry

`ptz_slew` was missing from `survsim/experiments/__init__.py::RUNNERS`, so `survsim experiment h56_ptz_slew` failed
and `tests/test_experiments.py::test_all_configs_load_and_name_a_runner` was red. Registered; every config's
runner (sensor_fusion, theta_policy, dose_fixedstep, quant_export, autocalib, reid_assoc, line_cross,
night_profiles, drift_monitor, evasion) was checked — all already present. 39/39 experiment tests pass.

## 6. Folded in

FACTS (H56 row rewritten, audit row, 2 ONVIF rows); 13_BASELINES experiments-summary row (the H56 line that had
been appended to `13_OPEN_QUESTIONS_AND_ROADMAP.md` was meant for this table and was moved); 52 and 64 register
rows; 64 H56 paragraph; 60 item 40; 48 Q (H56); 74 drill 1 PTZ count; 65 v2 item 31; 66 H56 done + H57
(re-detect-before-trust, σ(d) framing) + H58 (occlusion on the PTZ path); 75 §4.4 and 76 cross-refs.
Note: 13_BASELINES' "H58 r3" row is report 58's loiter round, not backlog H58.
