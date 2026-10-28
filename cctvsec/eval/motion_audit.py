"""Motion audit: are people in the ground truth moving the way their labels say?

Reads `gt/world.parquet` (and `meta/scenario.resolved.json` when present) from a
run directory and reports, per agent and overall:

* fraction of time stationary while the behaviour label implies walking;
* *stuck episodes* — more than `min_stuck_s` consecutive stationary seconds
  under a walking label, or with no behaviour at all (`normal.idle`, i.e. the
  plan ran out and the agent was left standing in the world);
* a probable cause for each episode: `plan_exhausted`, `avoidance_deadlock`
  (another person within `contact_m` for most of it), `goal_congestion` (at a
  shared goal — zone centroid / spawn / exit — with others), `unreachable_goal`
  (walking label, stationary, alone, far from any goal), or `waiting` (reported
  separately: a waiting label is supposed to be stationary);
* the distribution of walking speeds (per-agent median over moving
  `normal.transit` seconds — pacing is deliberately slower and excluded);
* how clustered people are at t=0 (the "everyone starts in one place" symptom).

Speeds are measured from *positions*, not the recorded velocity, because truth
is what happened: an agent whose velocity is set but whose position is pinned by
avoidance is stuck.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

STATIONARY_MPS = 0.2
# Labels whose behaviour means "you should be moving".
WALKING_PREFIXES = (
    "normal.transit", "normal.counter_flow", "normal.group_walk", "normal.night_presence",
    "suspicious.object.abandon", "suspicious.probe", "suspicious.follow",
)
WALKING_SUFFIXES = (".pace",)
IDLE_LABEL = "normal.idle"


def implies_walking(label: str) -> bool:
    return label.startswith(WALKING_PREFIXES) or label.endswith(WALKING_SUFFIXES)


def _goal_points(run_dir: Path) -> np.ndarray:
    p = run_dir / "meta" / "scenario.resolved.json"
    if not p.exists():
        return np.zeros((0, 2))
    env = json.loads(p.read_text()).get("environment", {})
    pts = [w["pos"][:2] for w in env.get("spawn_points", []) + env.get("exits", [])]
    for z in env.get("zones", []):
        poly = np.asarray(z["polygon"], dtype=float)
        pts.append(poly.mean(axis=0).tolist())
    return np.asarray(pts, dtype=float) if pts else np.zeros((0, 2))


def audit(run_dir: str | Path, min_stuck_s: float = 3.0, contact_m: float = 1.0) -> dict[str, Any]:
    import pandas as pd

    run_dir = Path(run_dir)
    df = pd.read_parquet(run_dir / "gt" / "world.parquet")
    goals = _goal_points(run_dir)
    df = df.sort_values(["uid", "t"])
    # Per-second samples: the frame closest to each whole second.
    df["sec"] = np.floor(df["t"] + 1e-6).astype(int)
    per_s = df.groupby(["uid", "sec"], as_index=False).first()
    pos_by_sec = {s: g[["x", "y"]].to_numpy() for s, g in per_s.groupby("sec")}
    uid_by_sec = {s: g["uid"].to_numpy() for s, g in per_s.groupby("sec")}

    agents: dict[str, Any] = {}
    episodes: list[dict[str, Any]] = []
    tot = {"agent_s": 0, "walk_s": 0, "walk_stationary_s": 0, "stuck_s": 0, "waiting_s": 0}
    walk_speeds: list[float] = []

    for uid, g in per_s.groupby("uid"):
        g = g.sort_values("sec")
        xy = g[["x", "y"]].to_numpy()
        secs = g["sec"].to_numpy()
        labels = g["label"].to_numpy()
        if len(xy) < 2:
            continue
        step = np.linalg.norm(np.diff(xy, axis=0), axis=1) / np.maximum(np.diff(secs), 1)
        # Speed over second k -> k+1 is attributed to second k's label.
        n = len(step)
        lab = labels[:n]
        walking = np.array([implies_walking(str(x)) for x in lab])
        idle = lab == IDLE_LABEL
        stationary = step < STATIONARY_MPS
        waiting = ~walking & ~idle
        tot["agent_s"] += n
        tot["walk_s"] += int(walking.sum())
        tot["walk_stationary_s"] += int((walking & stationary).sum())
        tot["waiting_s"] += int((waiting & stationary).sum())
        transit = np.array([str(x).startswith("normal.transit") for x in lab])
        moving_walk = step[transit & ~stationary]
        med = float(np.median(moving_walk)) if len(moving_walk) else None
        if med is not None:
            walk_speeds.append(med)

        bad = stationary & (walking | idle)
        agent_stuck = 0
        i = 0
        while i < n:
            if not bad[i]:
                i += 1
                continue
            j = i
            while j < n and bad[j]:
                j += 1
            dur = j - i
            if dur > min_stuck_s:
                ep_labels = lab[i:j]
                cause = _cause(uid, secs[i:j], ep_labels, xy[i:j], pos_by_sec, uid_by_sec,
                               goals, contact_m)
                episodes.append({"uid": uid, "t_start": int(secs[i]), "dur_s": int(dur),
                                 "label": str(ep_labels[0]), "cause": cause,
                                 "pos": [round(float(v), 2) for v in xy[i]]})
                agent_stuck += dur
            i = j
        tot["stuck_s"] += agent_stuck
        agents[uid] = {
            "seconds": n,
            "walk_s": int(walking.sum()),
            "walk_stationary_frac": round(float((walking & stationary).sum() / max(walking.sum(), 1)), 4),
            "stuck_s": int(agent_stuck),
            "median_walk_speed": None if med is None else round(med, 3),
        }

    # t=0 clustering: nearest-neighbour distance at the first frame.
    first = df[df["frame"] == df["frame"].min()][["x", "y"]].to_numpy()
    if len(first) > 1:
        d = np.linalg.norm(first[:, None] - first[None], axis=2)
        np.fill_diagonal(d, np.inf)
        nn = d.min(axis=1)
        t0 = {"n": len(first), "median_nn_m": round(float(np.median(nn)), 3),
              "frac_within_1m": round(float((nn < 1.0).mean()), 3),
              "distinct_cells_2m": len({(int(x // 2), int(y // 2)) for x, y in first})}
    else:
        t0 = {"n": len(first)}

    causes: dict[str, int] = {}
    for e in episodes:
        causes[e["cause"]] = causes.get(e["cause"], 0) + e["dur_s"]
    ws = np.asarray(walk_speeds)
    speed = ({"n_agents": len(ws), "min": round(float(ws.min()), 3),
              "p10": round(float(np.percentile(ws, 10)), 3),
              "median": round(float(np.median(ws)), 3),
              "p90": round(float(np.percentile(ws, 90)), 3), "max": round(float(ws.max()), 3),
              "std": round(float(ws.std()), 3),
              "frac_in_0.8_1.8": round(float(((ws >= 0.8) & (ws <= 1.8)).mean()), 3)}
             if len(ws) else {"n_agents": 0})
    return {
        "run_dir": str(run_dir),
        "agents": len(agents),
        "agent_seconds": tot["agent_s"],
        "stuck_fraction": round(tot["stuck_s"] / max(tot["agent_s"], 1), 4),
        "walk_stationary_fraction": round(tot["walk_stationary_s"] / max(tot["walk_s"], 1), 4),
        "waiting_stationary_s": tot["waiting_s"],
        "stuck_seconds_by_cause": causes,
        "n_stuck_episodes": len(episodes),
        "episodes": episodes,
        "walking_speed": speed,
        "t0_clustering": t0,
        "per_agent": agents,
    }


def _cause(uid, secs, labels, xy, pos_by_sec, uid_by_sec, goals, contact_m) -> str:
    if all(str(x) == IDLE_LABEL for x in labels):
        return "plan_exhausted"
    near_other = 0
    for s, p in zip(secs, xy):
        others = pos_by_sec[s][uid_by_sec[s] != uid]
        if len(others) and np.linalg.norm(others - p, axis=1).min() < contact_m:
            near_other += 1
    crowded = near_other >= 0.5 * len(secs)
    at_goal = len(goals) and np.linalg.norm(goals - xy.mean(axis=0), axis=1).min() < 2.0
    if crowded and at_goal:
        return "goal_congestion"
    if crowded:
        return "avoidance_deadlock"
    return "unreachable_goal"


def table(report: dict[str, Any]) -> str:
    sp = report["walking_speed"]
    lines = [
        f"run: {report['run_dir']}",
        f"agents={report['agents']}  agent-seconds={report['agent_seconds']}",
        f"stuck fraction           {report['stuck_fraction']:.2%}  ({report['n_stuck_episodes']} episodes >3 s)",
        f"stationary while walking {report['walk_stationary_fraction']:.2%}",
        f"stuck seconds by cause   {report['stuck_seconds_by_cause']}",
        f"waiting (stationary, ok) {report['waiting_stationary_s']} s",
        f"walking speed m/s        {sp}",
        f"t=0 clustering           {report['t0_clustering']}",
    ]
    return "\n".join(lines)
