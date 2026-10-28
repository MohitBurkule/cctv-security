"""H62 evaluation (docs/research/32 H62): position/time-keyed alarm scoring vs
actor-aware and window-only, on H59's calibrated-arm tailgate worlds.

Bounded: 100 tailgate worlds x 10 seeds x 3 fusion combos (C, C+abc, C+abcg),
calibrated arm only (the arm H59 found the actor-aware collapse on). Uses
`fuse_world_h54(..., with_positions=True)` (new, additive param) to get
per-alarm estimated/true positions that H59's own cache never stored, then
scores with `cctvsec.eval.alarms.score` in all three modes.

CPU only, <=4 workers, single pass, no polling.
"""
from __future__ import annotations

import json
import multiprocessing as mp
from pathlib import Path

from cctvsec.eval.alarms import Alarm, TruthEvent, score
from cctvsec.experiments import load_config
from cctvsec.experiments import sensor_fusion as S

N_TAILGATE = 100
N_SEEDS = 10
ARMS = ("C", "C+abc", "C+abcg")
RADII = (1.0, 2.0, 3.0)
TOLERANCE_S = 10.0


def _job(i):
    cfg = load_config("h59_idsw_fusion")
    # calibrated-arm hazard, exactly as computed by run_h59's own exposure pre-pass
    # over all H59 worlds (out/experiments/h59_idsw_fusion/results.json config.h59._h.calibrated)
    h = 0.13202911155381533  # calibrated arm (out/experiments/h59_idsw_fusion/results.json config.h59._h.calibrated)
    r_m = cfg["h59"]["r_m"]
    w = {"mode": "recall", "kind": "tailgate", "i": i}
    e = S.exposure_h59(w, cfg)
    per_seed = []
    for sd in range(N_SEEDS):
        r = S.fuse_world_h54(
            w, cfg, {"h": h, "seed": sd, "r_m": r_m, "cp": e["cp"]}, with_positions=True
        )
        per_seed.append(r)
    return per_seed


def main():
    with mp.Pool(4) as pool:
        results = pool.map(_job, range(N_TAILGATE))

    # Score each (world, seed) *independently* -- times are local to each world
    # (duration_s ~300 s, all starting near t=0), so pooling truths/alarms across
    # worlds into one score() call would let an alarm from one world spuriously
    # match a truth event's window in another. Sum tp/n over instances instead
    # (equivalent to a pooled recall, without the cross-world collision).
    import math

    n_instances = 0
    per_arm_sums = {
        a: {"aa_tp": 0, "wo_tp": 0, "n": 0, "pt_tp": {r: 0 for r in RADII},
            "pt_fc_hit": {r: 0 for r in RADII}, "pt_fc_elig": {r: 0 for r in RADII},
            "pt_static_tp": {r: 0 for r in RADII}}
        for a in ARMS
    }
    for per_seed in results:
        for r in per_seed:
            if not r["truth"]:
                continue
            ev = r["truth"][0]
            te = TruthEvent(
                t_start=ev["t"], t_end=ev["t"] + TOLERANCE_S, label="tailgate",
                actors=(ev["actor"],),
                actor_pos={ev["actor"]: ev["pos"]} if ev["pos"] is not None else None,
            )
            n_instances += 1
            for arm in ARMS:
                rows = r["fused"]["base"]["est"][arm]
                al = [Alarm(t=row[0], label="tailgate", uid=row[1], pos=row[4]) for row in rows]
                s = per_arm_sums[arm]
                s["n"] += 1
                s["aa_tp"] += score([te], al, camera_hours=1.0, tolerance_s=TOLERANCE_S,
                                     actor_aware=True).true_positives
                s["wo_tp"] += score([te], al, camera_hours=1.0, tolerance_s=TOLERANCE_S,
                                     actor_aware=False).true_positives
                # Static (alarms.score's own, t_start-anchored) position_time, for
                # completeness/API validation -- expected to undercount for a moving
                # actor over a 10 s window (see fuse_world_h54's with_positions note).
                for r_m_ in RADII:
                    ps = score([te], al, camera_hours=1.0, tolerance_s=TOLERANCE_S,
                               actor_aware=True, position_radius_m=r_m_)
                    if ps.position_time_recall:
                        s["pt_static_tp"][r_m_] += 1
                # Dynamic (per-alarm actor position at the alarm's own time) position_time
                # -- the headline H62 number. A hit requires the window match (same as
                # window-only) AND the alarm's est_pos within r of the actor's *own*
                # position at that alarm's timestamp (row[5][actor]).
                for r_m_ in RADII:
                    hit_evt = False
                    fc_evt = False
                    for row in rows:
                        ta, _uid, _src, _kd, est_pos, actor_pos_now, body = row
                        if not (ev["t"] <= ta <= ev["t"] + TOLERANCE_S):
                            continue
                        apos = actor_pos_now.get(ev["actor"])
                        if est_pos is None or apos is None:
                            continue
                        d = math.hypot(est_pos[0] - apos[0], est_pos[1] - apos[1])
                        if d <= r_m_:
                            hit_evt = True
                            # false credit: the alarm's *true physical source* is not the
                            # offending actor even though its position landed within r of
                            # the actor -- a bystander standing close enough to be
                            # attributed to the actor by position alone.
                            if body is not None and body != ev["actor"]:
                                fc_evt = True
                    if hit_evt:
                        s["pt_tp"][r_m_] += 1
                        s["pt_fc_elig"][r_m_] += 1
                        if fc_evt:
                            s["pt_fc_hit"][r_m_] += 1

    out = {"n_instances": n_instances, "arms": {}}
    for arm in ARMS:
        s = per_arm_sums[arm]
        n = s["n"]
        out["arms"][arm] = {
            "actor_aware_recall": s["aa_tp"] / n if n else None,
            "window_only_recall": s["wo_tp"] / n if n else None,
            "position_time_dynamic": {
                str(r_m_): {
                    "recall": s["pt_tp"][r_m_] / n if n else None,
                    "false_credit_rate": (
                        s["pt_fc_hit"][r_m_] / s["pt_fc_elig"][r_m_] if s["pt_fc_elig"][r_m_] else None
                    ),
                }
                for r_m_ in RADII
            },
            "position_time_static_t_start": {
                str(r_m_): {"recall": s["pt_static_tp"][r_m_] / n if n else None}
                for r_m_ in RADII
            },
            "n_events": n,
        }
    Path("out/experiments/h62_position_time_score").mkdir(parents=True, exist_ok=True)
    Path("out/experiments/h62_position_time_score/results_calibrated.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
