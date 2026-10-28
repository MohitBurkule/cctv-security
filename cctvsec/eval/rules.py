"""A baseline dwell-time rule engine — the thing every vendor ships first.

It runs on perfect tracks from the simulator, so its errors are not perception
errors: they are the errors the *rule itself* makes. That separation is the point.
Given flawless detection and tracking, a dwell-time loitering rule still fires on
every commuter waiting for a train, which is why loitering analytics have a
reputation for nuisance alarms.

Use it as the floor that any learned behaviour classifier must beat.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from .alarms import Alarm


@dataclass
class DwellRule:
    """Fire when a person stays inside a tagged zone for longer than a threshold."""

    threshold_s: float = 60.0
    zone_tags: tuple[str, ...] = ("gate", "restricted", "perimeter_fence")
    speed_cap_mps: float = 0.5
    label: str = "suspicious.loiter"

    def run(self, world_df: pd.DataFrame, zone_tag_by_id: dict[str, str]) -> list[Alarm]:
        alarms: list[Alarm] = []
        if world_df.empty:
            return alarms

        df = world_df.sort_values(["uid", "t"])
        for uid, person in df.groupby("uid", sort=False):
            dwell_start: float | None = None
            current_zone: str | None = None
            fired_for_zone: set[str] = set()

            for row in person.itertuples():
                zone = row.zone
                eligible = (
                    zone is not None
                    and zone_tag_by_id.get(zone) in self.zone_tags
                    and float(row.speed) <= self.speed_cap_mps
                )
                if not eligible:
                    dwell_start, current_zone = None, None
                    continue
                if zone != current_zone:
                    dwell_start, current_zone = float(row.t), zone
                    continue
                assert dwell_start is not None
                if float(row.t) - dwell_start >= self.threshold_s and zone not in fired_for_zone:
                    alarms.append(Alarm(t=float(row.t), label=self.label, uid=str(uid)))
                    fired_for_zone.add(zone)
        return alarms


@dataclass
class AbandonedObjectRule:
    """Fire when a dropped object stays put and its owner walks far enough away."""

    static_s: float = 30.0
    owner_distance_m: float = 15.0
    label: str = "suspicious.object.abandon"

    def run(self, objects: dict[str, dict[str, Any]], world_df: pd.DataFrame) -> list[Alarm]:
        import numpy as np

        alarms: list[Alarm] = []
        for obj in objects.values():
            owner_track = world_df[world_df["uid"] == obj["owner"]]
            if owner_track.empty:
                continue
            pos = np.asarray(obj["pos"], dtype=float)
            after = owner_track[owner_track["t"] >= obj["t_drop"]]
            d = np.linalg.norm(after[["x", "y"]].to_numpy() - pos, axis=1)
            far = after["t"].to_numpy()[d >= self.owner_distance_m]
            if len(far):
                alarms.append(Alarm(t=float(far[0]), label=self.label, uid=str(obj["owner"])))
        return alarms


def run_baseline(run_dir: Path, threshold_s: float = 60.0) -> list[Alarm]:
    """Run the dwell rule over a recorded run and return its alarms."""
    import json

    run_dir = Path(run_dir)
    world = pd.read_parquet(run_dir / "gt" / "world.parquet")
    scenario = json.loads((run_dir / "meta" / "scenario.resolved.json").read_text())
    tags = {z["id"]: z["tag"] for z in scenario["environment"]["zones"]}
    return DwellRule(threshold_s=threshold_s).run(world, tags)


@dataclass
class PathLoiterRule:
    """A loitering rule keyed on displacement, not on instantaneous speed or the
    formal zone a point happens to fall in.

    `DwellRule` (above) is the naive vendor-default baseline, and it fails in two
    directions that show up together on `disguise_and_tamper`:

    1. **It misses real loiterers who drift.** A pacing person's *instantaneous*
       speed is well above any sensible "stationary" cap, and their path can wander
       across a zone boundary. A rule keyed on "speed <= cap AND zone tag
       unchanged" can lose the loiterer the moment either of those technicalities
       breaks, even though the person never actually went anywhere.
    2. **It fires on people who are legitimately still.** A worker standing next
       to their equipment for a 90 s job looks, to a dwell-time rule, identical to
       a loiterer — that is deliberately the hard-negative pairing (docs/03 §1,
       docs/research/19 §"Loitering").

    The fix here has three parts:

    * **Displacement radius, not speed.** Loitering is "has not gone anywhere",
      which is a property of *where the track has been over a trailing window*,
      not of the current instantaneous velocity. We track the 90th-percentile
      distance from the running centroid of the last `window_s` seconds (matching
      report 19 §2.1's `spread(g)`) and require it to stay within `radius_m`.
    * **Re-entry tolerance.** A brief step outside the radius (or a `None` zone
      sample from a dropped frame) does not reset the clock; the dwell only
      resets after `reentry_gap_s` of continuous departure. This is what lets a
      pacer who overshoots the nominal zone boundary still count.
    * **Role/context exemption.** A zone's `allowed_roles` (docs/research/19
      "role context") authorises the roles it lists; someone with that role
      dwelling inside that specific zone is not alarmed on. `World.zone_of` (and
      the `world_df["zone"]` column it produces) now resolves nested/overlapping
      zones to the smallest containing one, so this reads `world_df["zone"]`
      directly instead of recomputing containment.
    """

    threshold_s: float = 60.0
    radius_m: float = 4.0
    reentry_gap_s: float = 20.0
    window_s: float = 30.0
    label: str = "suspicious.loiter"

    def run(
        self,
        world_df: pd.DataFrame,
        zones: list[dict[str, Any]],
        role_by_uid: dict[str, str] | None = None,
    ) -> list[Alarm]:
        import numpy as np

        alarms: list[Alarm] = []
        if world_df.empty:
            return alarms
        role_by_uid = role_by_uid or {}
        roles_by_zone: dict[str, list[str]] = {
            z["id"]: (z.get("allowed_roles") or []) for z in zones
        }

        df = world_df.sort_values(["uid", "t"])
        for uid, person in df.groupby("uid", sort=False):
            role = role_by_uid.get(uid)
            ts = person["t"].to_numpy(dtype=float)
            xs = person["x"].to_numpy(dtype=float)
            ys = person["y"].to_numpy(dtype=float)
            zs = person["zone"].to_numpy(dtype=object) if "zone" in person else np.full(len(ts), None)

            window_t: list[float] = []
            window_xy: list[tuple[float, float]] = []
            dwell_start: float | None = None  # start of the current unbroken dwell
            outside_since: float | None = None
            fired = False

            def reset() -> None:
                nonlocal window_t, window_xy, dwell_start, outside_since, fired
                window_t, window_xy = [], []
                dwell_start, outside_since, fired = None, None, False

            for t, x, y, zid in zip(ts, xs, ys, zs):
                roles = roles_by_zone.get(zid, []) if zid is not None else []
                if role is not None and role in roles:
                    # Authorised presence in this specific zone: never a loiter
                    # candidate here, no matter how long they dwell.
                    reset()
                    continue

                # `window_*` is only for the trailing spread(g) estimate (report 19
                # §2.1); `dwell_start` tracks the whole unbroken dwell and must not
                # be trimmed by it, or `threshold_s > window_s` could never fire.
                window_t.append(t)
                window_xy.append((x, y))
                while window_t and t - window_t[0] > self.window_s:
                    window_t.pop(0)
                    window_xy.pop(0)
                if dwell_start is None:
                    dwell_start = t

                pts = np.asarray(window_xy)
                centroid = pts.mean(axis=0)
                spread = float(np.percentile(np.linalg.norm(pts - centroid, axis=1), 90)) if len(pts) else 0.0

                if spread <= self.radius_m:
                    outside_since = None
                else:
                    if outside_since is None:
                        outside_since = t
                    if t - outside_since > self.reentry_gap_s:
                        # Genuinely moved on: start a fresh dwell.
                        reset()
                        window_t, window_xy = [t], [(x, y)]
                        dwell_start = t
                        continue

                dwell = t - dwell_start
                if dwell >= self.threshold_s and not fired:
                    alarms.append(Alarm(t=float(t), label=self.label, uid=str(uid)))
                    fired = True
        return alarms


# ---------------------------------------------------------------- redesign (58)
# docs/research/58_LOITER_RULE_REDESIGN.md. Every rule below keeps the
# `run(world_df, zones, role_by_uid)` interface of `PathLoiterRule`, but works
# on the 1 s tick feature table from `loiter_features.world_feature_table`, and
# exposes `fire(table)` so a batch evaluator can reuse a cached table and get
# exactly the alarms `run` would.


def _tag_ok(table: pd.DataFrame, zone_tags: tuple[str, ...] | None):
    import numpy as np
    if zone_tags is None:
        return np.ones(len(table), bool)
    return table["tag"].isin(list(zone_tags)).to_numpy()


class _TickRule:
    label: str = "suspicious.loiter"

    def condition(self, table: pd.DataFrame):  # pragma: no cover - abstract
        raise NotImplementedError

    def fire(self, table: pd.DataFrame) -> list[float]:
        """Alarm times: the first qualifying tick of each dwell episode, never in
        a zone where the person's role is authorised."""
        return [t for t, _ in self.fire_with_uid(table)]

    def fire_with_uid(self, table: pd.DataFrame) -> list[tuple[float, str]]:
        """`fire`, with the uid of the person each alarm is about."""
        from .loiter_features import first_per_episode
        if table.empty:
            return []
        cond = self.condition(table) & ~table["allowed"].to_numpy(bool)
        idx = first_per_episode(cond, table["ep"].to_numpy())
        return [(float(t), str(u)) for t, u in zip(table["t"].to_numpy()[idx], table["uid"].to_numpy()[idx])]

    def run(self, world_df: pd.DataFrame, zones: list[dict[str, Any]],
            role_by_uid: dict[str, str] | None = None, spawns=None) -> list[Alarm]:
        from .loiter_features import world_feature_table
        table = world_feature_table(world_df, zones, role_by_uid, spawns)
        return [Alarm(t=t, label=self.label, uid=u) for t, u in sorted(self.fire_with_uid(table))]


@dataclass
class ZoneDwellRule(DwellRule):
    """C1: `DwellRule` with zone semantics.

    Zones whose tag is in `exempt_tags` (a site's commute / queue / public-wait
    areas) or whose id is in `exempt_zone_ids` never start a dwell, and a
    person whose role a zone's `allowed_roles` authorises is exempt there."""

    exempt_tags: tuple[str, ...] = ("queue",)
    exempt_zone_ids: tuple[str, ...] = ()

    def run(self, world_df: pd.DataFrame, zones: list[dict[str, Any]],  # type: ignore[override]
            role_by_uid: dict[str, str] | None = None) -> list[Alarm]:
        role_by_uid = role_by_uid or {}
        tags = {z["id"]: z["tag"] for z in zones
                if z["tag"] not in self.exempt_tags and z["id"] not in self.exempt_zone_ids}
        allowed = {z["id"]: set(z.get("allowed_roles") or []) for z in zones}
        if world_df.empty:
            return []
        df = world_df.copy()
        roles = df["uid"].map(lambda u: role_by_uid.get(u))
        auth = [r is not None and r in allowed.get(z, ()) for z, r in zip(df["zone"], roles)]
        df.loc[auth, "zone"] = None
        return DwellRule.run(self, df, tags)


@dataclass
class DisplacementLoiterRule(_TickRule):
    """C2: loiter clock keyed on *net displacement*.

    The clock (`clock` feature) restarts whenever the person's net displacement
    over the trailing 10 s exceeds 4 m - a walker restarts it every tick, so
    unlike `PathLoiterRule` (which only resets after `reentry_gap_s` of
    continuous movement) ordinary transit can never accumulate dwell. The
    30 s stationary fraction must lie in [stat_lo, stat_hi]: stat_hi < 1
    rejects people standing still (waits, queues, phone calls), which is the
    kinematic difference between pacing and waiting."""

    threshold_s: float = 20.0
    stat_lo: float = 0.0
    stat_hi: float = 1.0
    min_moving: float = 0.0
    zone_tags: tuple[str, ...] | None = None

    def condition(self, table: pd.DataFrame):
        c = table["clock"].to_numpy() >= self.threshold_s
        s = table["stat30"].to_numpy()
        c &= (s >= self.stat_lo) & (s <= self.stat_hi)
        c &= table["moving30"].to_numpy() >= self.min_moving
        return c & _tag_ok(table, self.zone_tags)


@dataclass
class RevisitRule(_TickRule):
    """C3: oscillation. Fires when, within the last 60 s, the person came back
    to within 1 m of an earlier position after having been > 2 m from it at
    least `min_revisits` times, while their dwell clock is >= `min_clock_s`."""

    min_revisits: int = 2
    min_clock_s: float = 10.0
    zone_tags: tuple[str, ...] | None = None

    def condition(self, table: pd.DataFrame):
        c = table["revisits60"].to_numpy() >= self.min_revisits
        c &= table["clock"].to_numpy() >= self.min_clock_s
        return c & _tag_ok(table, self.zone_tags)


@dataclass
class LearnedLoiterRule(_TickRule):
    """C4: logistic score on the hand features (`loiter_features.FEATURES`),
    trained offline (tools/loiter_eval.py fit). Fires once per dwell episode
    when p >= theta and the dwell clock is >= `min_clock_s`; `gate` optionally
    ANDs another tick rule's condition (C5)."""

    weights: tuple[float, ...] = ()
    bias: float = 0.0
    mean: tuple[float, ...] = ()
    std: tuple[float, ...] = ()
    features: tuple[str, ...] = ()
    log1p: tuple[str, ...] = ()
    theta: float = 0.5
    min_clock_s: float = 5.0
    gate: Any = None

    def score(self, table: pd.DataFrame):
        import numpy as np
        X = np.array(table[list(self.features)].to_numpy(float), copy=True)
        for j, name in enumerate(self.features):
            if name in self.log1p:
                X[:, j] = np.log1p(np.maximum(X[:, j], 0.0))
        z = (X - np.asarray(self.mean)) / np.asarray(self.std)
        return 1.0 / (1.0 + np.exp(-(z @ np.asarray(self.weights) + self.bias)))

    def condition(self, table: pd.DataFrame):
        c = (self.score(table) >= self.theta) & (table["clock"].to_numpy() >= self.min_clock_s)
        if self.gate is not None:
            c &= self.gate.condition(table)
        return c


@dataclass
class GBMLoiterRule(_TickRule):
    """Round 3 (58 §7): tree-ensemble score on the same tick features as
    `LearnedLoiterRule`. `model` is any fitted classifier with
    `predict_proba` (sklearn `HistGradientBoostingClassifier` in the
    experiment); `calibrator`, if set, maps the raw score to a calibrated
    probability (`predict`, e.g. `IsotonicRegression`) and `theta` is then on
    the calibrated scale. Features named in `CONTEXT_FEATURES` are added from
    the `zone` column when absent."""

    model: Any = None
    features: tuple[str, ...] = ()
    calibrator: Any = None
    theta: float = 0.5
    min_clock_s: float = 5.0

    def score(self, table: pd.DataFrame):
        import numpy as np

        from .loiter_features import CONTEXT_FEATURES, add_context
        if any(f in CONTEXT_FEATURES and f not in table for f in self.features):
            table = add_context(table.copy())
        p = self.model.predict_proba(table[list(self.features)].to_numpy(np.float32))[:, 1]
        return self.calibrator.predict(p) if self.calibrator is not None else p

    def condition(self, table: pd.DataFrame):
        return (self.score(table) >= self.theta) & (table["clock"].to_numpy() >= self.min_clock_s)


@dataclass
class AllOfRule(_TickRule):
    """C5: fire only where every member tick rule's condition holds."""

    rules: tuple[Any, ...] = ()

    def condition(self, table: pd.DataFrame):
        import numpy as np
        c = np.ones(len(table), bool)
        for r in self.rules:
            c &= r.condition(table)
        return c


def run_path_loiter_baseline(
    run_dir: Path,
    threshold_s: float = 60.0,
    radius_m: float = 4.0,
    reentry_gap_s: float = 20.0,
) -> list[Alarm]:
    """Run `PathLoiterRule` over a recorded run and return its alarms."""
    import json

    run_dir = Path(run_dir)
    world = pd.read_parquet(run_dir / "gt" / "world.parquet")
    scenario = json.loads((run_dir / "meta" / "scenario.resolved.json").read_text())
    zones = scenario["environment"]["zones"]

    role_by_uid: dict[str, str] = {}
    identities_path = run_dir / "gt" / "identities.parquet"
    if identities_path.exists():
        idf = pd.read_parquet(identities_path)
        for row in idf.itertuples():
            role_by_uid[row.uid] = row.role

    return PathLoiterRule(
        threshold_s=threshold_s, radius_m=radius_m, reentry_gap_s=reentry_gap_s
    ).run(world, zones, role_by_uid)
