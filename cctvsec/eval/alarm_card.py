"""Alarm cards (docs/research/86 §7, H60): one card per alarm, built from what a run emits.

Two modes, and the difference is the point:

* ``mode="sim"`` may read ground truth (``gt/``): zone from ``world.parquet``, box +
  visibility from ``gt/mot_<cam>.txt``, tamper/blind truth from ``camera_status.jsonl``,
  and the simulator-only verdict ``gt_match`` (hit / repeat / late / wrong_actor / false)
  with its i-LIDS delay.
* ``mode="real"`` carries only what a deployed site has: the alarm's time, label and
  camera, a *tracker* track id if the alarm source supplied one, the PTZ pose the head
  reports, calibration, the licences reference and runner-supplied score/θ/rank. A GT
  uid on an alarm (``eval.rules`` alarms carry one) is **dropped**, not relabelled —
  on a real site it would be a fabricated identity (66 H60 "confounds").

The guard is a key whitelist per mode (:data:`REAL_KEYS`) checked on every card, plus
:func:`leak_count`, which greps the serialised card for every sim-only key and every
GT value (uids, event ids) a run contains.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .alarms import DEFAULT_TOLERANCE_S, Alarm, TruthEvent

#: keys a real-mode card may carry (top level, and inside nested dicts listed below).
REAL_KEYS = frozenset({
    "alarm_id", "mode", "t", "label", "camera_id", "track_id", "calib_ref", "camera_pose",
    "score", "theta", "rank_in_queue", "licences_ref", "run_id",
    "config_hash", "model_hash", "clip_hash",
})
#: clip_hash value when the run dir holds no frames for the alarm window.
CLIP_NOT_EMITTED = "not emitted"
CLIP_HALF_WINDOW_S = 5.0
REAL_POSE_KEYS = frozenset({"yaw", "pitch", "hfov_deg", "t_status"})
#: keys only a simulator can fill. None of these strings may appear in a real card.
SIM_ONLY_KEYS = frozenset({
    "gt_match", "event_id", "i_lids_delay_s", "zone_id", "box_xywh", "visibility",
    "gt_uid", "camera_health", "tamper", "blind",
})
SIM_KEYS = REAL_KEYS | SIM_ONLY_KEYS
MODES = ("sim", "real")


@dataclass(frozen=True)
class RunnerFields:
    """Per-alarm values a runner holds in memory (H22/H33): score, θ, queue rank."""
    score: float | None = None
    theta: float | None = None
    rank_in_queue: int | None = None


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def clip_hash(run_dir: Path, camera: str | None, t: float, fps: float,
              half_window_s: float = CLIP_HALF_WINDOW_S) -> str:
    """sha256 over ``frames/<cam>/NNNN.{png,jpg}`` with frame/fps in [t-w, t+w].

    Each frame contributes ``relative path || sha256(file)`` in frame order, so a renamed,
    dropped or edited frame changes the hash. No frames => :data:`CLIP_NOT_EMITTED`.
    """
    root = Path(run_dir) / "frames"
    cams = [camera] if camera else (sorted(p.name for p in root.iterdir() if p.is_dir())
                                    if root.is_dir() else [])
    picked = []
    for c in cams:
        d = root / c
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if f.suffix.lower() in (".png", ".jpg", ".jpeg") and f.stem.isdigit():
                tf = int(f.stem) / fps
                if t - half_window_s - 1e-9 <= tf <= t + half_window_s + 1e-9:
                    picked.append((c, int(f.stem), f))
    if not picked:
        return CLIP_NOT_EMITTED
    h = hashlib.sha256()
    for c, _n, f in sorted(picked):
        h.update(f"{c}/{f.name}|{sha256_file(f)}\n".encode())
    return h.hexdigest()


def alarm_id(run_id: str, a: Alarm, track: str | None, index: int) -> str:
    """Deterministic id: sha256 of run id, camera, t (ms), tracker id, label and alarm index.

    Deliberately *not* the GT uid: even hashed, it would carry ground truth into a real card.
    """
    key = f"{run_id}|{a.camera or ''}|{round(a.t * 1000)}|{track or ''}|{a.label}|{index}"
    return hashlib.sha256(key.encode()).hexdigest()[:16]


def _read_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def _status_at(rows: list[dict], camera: str, t: float) -> dict | None:
    best = None
    for r in rows:
        if r["camera"] == camera and r["t"] <= t + 1e-9 and (best is None or r["t"] >= best["t"]):
            best = r
    return best


def _label_matches(alarm_label: str, ev_label: str) -> bool:
    return ev_label == alarm_label or ev_label.startswith(alarm_label + ".")


def gt_matches(
    alarms: list[Alarm], truth: list[TruthEvent], tolerance_s: float = DEFAULT_TOLERANCE_S,
    event_ids: list[str] | None = None,
) -> dict[int, dict]:
    """Per-alarm i-LIDS verdict, replicating ``alarms.score`` actor-aware matching.

    Returns ``{index into alarms: {verdict, event_id, i_lids_delay_s}}``. ``hit`` = first
    alarm in an event's window [t_start, t_start + tol] (actor must match when the alarm
    has a uid); ``repeat`` = another alarm in an already-matched window; ``late`` = right
    actor and label, after the window; ``wrong_actor`` = in a window of an event of the
    right label but not on one of its actors; ``false`` = anything else.
    """
    order = sorted(range(len(alarms)), key=lambda i: alarms[i].t)
    matched: set[int] = set()
    out: dict[int, dict] = {}
    ids = event_ids or [f"idx_{i}" for i in range(len(truth))]

    def actor_ok(a: Alarm, ev: TruthEvent) -> bool:
        return a.uid is None or not ev.actors or a.uid in ev.actors

    for i in order:
        a = alarms[i]
        verdict, hit = "false", None
        for j, ev in enumerate(truth):
            if not _label_matches(a.label, ev.label) or not actor_ok(a, ev):
                continue
            if ev.t_start <= a.t <= ev.t_start + tolerance_s:
                hit = j
                break
        if hit is not None:
            verdict = "repeat" if hit in matched else "hit"
            matched.add(hit)
            out[i] = {"verdict": verdict, "event_id": ids[hit],
                      "i_lids_delay_s": round(a.t - truth[hit].t_start, 3)}
            continue
        late = [j for j, ev in enumerate(truth)
                if _label_matches(a.label, ev.label) and actor_ok(a, ev) and a.t > ev.t_start + tolerance_s
                and a.t <= ev.t_end + tolerance_s]
        wrong = [j for j, ev in enumerate(truth)
                 if _label_matches(a.label, ev.label) and not actor_ok(a, ev)
                 and ev.t_start <= a.t <= ev.t_start + tolerance_s]
        if late:
            j = late[0]
            out[i] = {"verdict": "late", "event_id": ids[j],
                      "i_lids_delay_s": round(a.t - truth[j].t_start, 3)}
        elif wrong:
            out[i] = {"verdict": "wrong_actor", "event_id": ids[wrong[0]], "i_lids_delay_s": None}
        else:
            out[i] = {"verdict": "false", "event_id": None, "i_lids_delay_s": None}
    return out


class _SimIndex:
    """GT lookups for sim mode only (world zone, MOT box, uid -> MOT id)."""

    def __init__(self, run_dir: Path):
        import pandas as pd

        self.world = pd.read_parquet(run_dir / "gt" / "world.parquet")
        tid = run_dir / "meta" / "track_ids.json"
        self.track_ids: dict[str, int] = json.loads(tid.read_text()) if tid.exists() else {}
        self.mot: dict[str, dict[tuple[int, int], tuple]] = {}
        for p in sorted((run_dir / "gt").glob("mot_*.txt")):
            cam = p.stem[len("mot_"):]
            rows: dict[tuple[int, int], tuple] = {}
            for line in p.read_text().splitlines():
                f = line.split(",")
                if len(f) >= 9:
                    rows[(int(f[0]), int(f[1]))] = (float(f[2]), float(f[3]), float(f[4]),
                                                   float(f[5]), float(f[8]))
            self.mot[cam] = rows

    def frame_at(self, t: float) -> int:
        w = self.world
        return int(w.iloc[(w["t"] - t).abs().argmin()]["frame"])

    def zone(self, uid: str, t: float) -> str | None:
        w = self.world[self.world["uid"] == uid]
        if w.empty:
            return None
        return str(w.iloc[(w["t"] - t).abs().argmin()]["zone"])

    def box(self, uid: str, t: float, camera: str | None) -> tuple[str, list[float], float] | None:
        mid = self.track_ids.get(uid)
        if mid is None:
            return None
        frame = self.frame_at(t)
        cams = [camera] if camera else sorted(self.mot)
        best = None
        for c in cams:
            r = self.mot.get(c, {}).get((frame, mid))
            if r and (best is None or r[4] > best[2]):
                best = (c, [round(v, 2) for v in r[:4]], r[4])
        return best


def build_cards(
    run_dir: Path, alarms: list[Alarm], mode: str = "sim",
    runner: dict[int, RunnerFields] | None = None,
    track_ids: dict[int, str] | None = None,
    truth: list[TruthEvent] | None = None, event_ids: list[str] | None = None,
    tolerance_s: float = DEFAULT_TOLERANCE_S,
    config_path: Path | None = None, model_path: Path | None = None,
) -> list[dict]:
    """One card per alarm, in alarm order.

    ``config_hash`` = sha256 of ``config_path`` (the scenario YAML) if given, else of
    ``meta/scenario.resolved.json``; ``model_hash`` = sha256 of the checkpoint at
    ``model_path`` (absent without one); ``clip_hash`` see :func:`clip_hash`.

    ``track_ids`` maps alarm index to a *tracker* track id (pipeline output); it is the
    only identity a real card may carry. ``truth``/``event_ids`` are used in sim mode only.
    """
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    run_dir = Path(run_dir)
    runner = runner or {}
    track_ids = track_ids or {}
    status = _read_jsonl(run_dir / "gt" / "camera_status.jsonl")
    lic = run_dir / "meta" / "licences.json"
    run_id = hashlib.sha256(
        (run_dir / "meta" / "scenario.resolved.json").read_bytes()).hexdigest()[:16]
    cfg_bytes = (Path(config_path) if config_path else
                 run_dir / "meta" / "scenario.resolved.json").read_bytes()
    config_hash = hashlib.sha256(cfg_bytes).hexdigest()
    model_hash = sha256_file(Path(model_path)) if model_path else None
    fps = float(json.loads((run_dir / "meta" / "scenario.resolved.json").read_text()).get("fps", 10.0))
    sim = _SimIndex(run_dir) if mode == "sim" else None
    matches = gt_matches(alarms, truth or [], tolerance_s, event_ids) if mode == "sim" else {}

    cards = []
    for i, a in enumerate(alarms):
        track = track_ids.get(i)
        camera = a.camera
        card: dict[str, Any] = {
            "alarm_id": alarm_id(run_id, a, track, i), "mode": mode, "run_id": run_id,
            "t": a.t, "label": a.label, "camera_id": camera, "track_id": track,
        }
        if sim is not None and a.uid is not None:
            card["gt_uid"] = a.uid
            card["zone_id"] = sim.zone(a.uid, a.t)
            b = sim.box(a.uid, a.t, camera)
            if b is not None:
                if camera is None:
                    camera = card["camera_id"] = b[0]
                card["box_xywh"], card["visibility"] = b[1], round(b[2], 3)
        if camera is not None:
            if (run_dir / "calib" / f"{camera}.json").exists():
                card["calib_ref"] = f"calib/{camera}.json"
            st = _status_at(status, camera, a.t)
            if st is not None:
                # A PTZ head reports its own pose, so pose is real-site data (principle 2:
                # the box/calib must follow the live head, not the configured preset).
                card["camera_pose"] = {"yaw": st["yaw"], "pitch": st["pitch"],
                                       "hfov_deg": st["hfov_deg"], "t_status": st["t"]}
                if sim is not None:
                    # Tamper/blind *truth* is simulator knowledge; a real site has only a
                    # tamper detector's opinion, which is a different field.
                    card["camera_health"] = ("blinded" if st.get("blind") else
                                             f"tamper:{st['tamper']}" if st.get("tamper") else "ok")
        rf = runner.get(i)
        if rf is not None:
            for k in ("score", "theta", "rank_in_queue"):
                if getattr(rf, k) is not None:
                    card[k] = getattr(rf, k)
        card["config_hash"] = config_hash
        if model_hash is not None:
            card["model_hash"] = model_hash
        card["clip_hash"] = clip_hash(run_dir, camera, a.t, fps)
        if lic.exists():
            card["licences_ref"] = "meta/licences.json"
        if sim is not None:
            card["gt_match"] = matches.get(i, {"verdict": "false", "event_id": None,
                                               "i_lids_delay_s": None})
            card["i_lids_delay_s"] = card["gt_match"]["i_lids_delay_s"]
        validate_card(card)
        cards.append(card)
    return cards


def validate_card(card: dict) -> None:
    """Schema check: every key must be allowed for the card's mode."""
    mode = card.get("mode")
    allowed = REAL_KEYS if mode == "real" else SIM_KEYS
    bad = set(card) - allowed
    if mode == "real" and "camera_pose" in card:
        bad |= set(card["camera_pose"]) - REAL_POSE_KEYS
    if bad:
        raise ValueError(f"{mode} card carries disallowed keys: {sorted(bad)}")


def gt_values(run_dir: Path) -> set[str]:
    """GT-only values a real card must not contain: uids, event ids and GT zone names."""
    run_dir = Path(run_dir)
    vals: set[str] = set()
    tid = run_dir / "meta" / "track_ids.json"
    if tid.exists():
        vals |= set(json.loads(tid.read_text()))
    for r in _read_jsonl(run_dir / "gt" / "events.jsonl"):
        if r.get("event_id"):
            vals.add(str(r["event_id"]))
        vals |= {str(x) for x in r.get("actors", [])}
    wp = run_dir / "gt" / "world.parquet"
    if wp.exists():
        import pandas as pd

        vals |= {str(z) for z in pd.read_parquet(wp, columns=["zone"])["zone"].dropna().unique()}
    ip = run_dir / "gt" / "identities.parquet"
    if ip.exists():
        import pandas as pd

        df = pd.read_parquet(ip)
        for col in df.columns:
            if df[col].dtype == object or str(df[col].dtype) in ("string", "str"):
                vals |= {str(v) for v in df[col].dropna().unique()}
    return vals


#: GT-derived strings a real card may legitimately contain (rule labels, generic vocabulary).
LEAK_ALLOWLIST = frozenset({
    "loiter", "intrusion", "tailgate", "abandon", "person", "normal", "none", "null",
    "true", "false",
})
#: GT values shorter than this are too generic to substring-match without false positives.
LEAK_MIN_LEN = 4


def _strings(v) -> Iterable[str]:
    if isinstance(v, str):
        yield v
    elif isinstance(v, dict):
        for x in v.values():
            yield from _strings(x)
    elif isinstance(v, (list, tuple)):
        for x in v:
            yield from _strings(x)


def leak_count(cards: Iterable[dict], gt_vals: Iterable[str] = ()) -> int:
    """Real-mode cards carrying any sim-only key, or any GT value as a substring of a string field.

    GT values in :data:`LEAK_ALLOWLIST` or shorter than :data:`LEAK_MIN_LEN` are skipped.
    """
    keys = [f'"{k}"' for k in SIM_ONLY_KEYS]
    vals = [v for v in {str(x) for x in gt_vals}
            if len(v) >= LEAK_MIN_LEN and v.lower() not in LEAK_ALLOWLIST]
    n = 0
    for c in cards:
        s = json.dumps(c, sort_keys=True)
        if any(x in s for x in keys) or any(
                v in f for f in _strings(c) for v in vals):
            n += 1
    return n
