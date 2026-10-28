"""End-to-end pipeline: generate a scene, run it, degrade it, export it, score it.

This exists to prove the chain holds together, and to fail loudly at whichever
link breaks. Every stage is one the project claims to support, so running this is
the shortest honest answer to "does it work?".

    generate scene -> simulate -> ground truth -> COCO export
                   -> degrade to CCTV profiles -> realism score
                   -> behaviour model -> alarm architecture -> operator metrics

It runs on the mock backend by default, so it needs no GPU and no engine. With
`--engine unreal` it drives the packaged build instead, and records whichever
capabilities that build turned out not to have.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


@dataclass
class DemoResult:
    stages: dict[str, Any] = field(default_factory=dict)
    failures: list[str] = field(default_factory=list)

    def record(self, name: str, payload: Any) -> None:
        self.stages[name] = payload

    def fail(self, name: str, error: Exception) -> None:
        self.failures.append(f"{name}: {type(error).__name__}: {error}")

    @property
    def ok(self) -> bool:
        return not self.failures

    def as_dict(self) -> dict[str, Any]:
        return {"ok": self.ok, "stages": self.stages, "failures": self.failures}


def run_demo(
    out_dir: Path,
    n_scenes: int = 4,
    duration_s: float = 120.0,
    fps: float = 5.0,
    seed: int = 0,
    engine: str = "mock",
) -> DemoResult:
    """Run every stage, collecting results and recording any that break."""
    import pandas as pd

    from .eval.alarms import TruthEvent
    from .eval.behaviour import (
        BehaviourClassifier,
        evaluate_classifier,
        extract_features,
        segments_from_world,
        split_by_identity,
    )
    from .eval.pipeline import AlarmPipeline, Candidate, compare_architectures
    from survsim.generator import generate_batch
    from survsim.simulator import Simulator

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    result = DemoResult()

    # ---- 1. generate diverse, validated scenes
    try:
        batch = generate_batch(n=n_scenes, seed=seed, duration_s=duration_s, fps=fps,
                               engine=engine)
        result.record("generate", {
            **batch.diversity(),
            "repairs": batch.repaired,
            "invalid": [s.scenario.name for s in batch.scenes if not s.valid],
        })
    except Exception as exc:  # noqa: BLE001
        result.fail("generate", exc)
        return result

    # ---- 2. simulate and write ground truth
    frames: list[Any] = []
    camera_hours = 0.0
    for i, scene in enumerate(batch.scenes):
        try:
            scene.scenario.name = f"demo_{i}"
            sim = Simulator(scene.scenario)
            run_dir = out_dir / f"scene_{i}"
            sim.record(run_dir, topdown_video=False)
            df = pd.read_parquet(run_dir / "gt" / "world.parquet")
            df["uid"] = f"s{i}_" + df["uid"].astype(str)
            frames.append(df)
            camera_hours += len(scene.scenario.cameras) * duration_s / 3600.0
            if isinstance(getattr(sim.backend, "limitations", None), list):
                result.record("engine_limitations", sim.backend.limitations)
        except Exception as exc:  # noqa: BLE001
            result.fail(f"simulate[{i}]", exc)

    if not frames:
        return result
    world = pd.concat(frames, ignore_index=True)
    result.record("simulate", {"scenes": len(frames), "rows": len(world),
                               "identities": int(world.uid.nunique()),
                               "camera_hours": round(camera_hours, 3)})

    # ---- 3. COCO export from the last scene's per-camera rows
    try:
        from survsim.gt.coco import from_camera_rows

        rows = []
        last = batch.scenes[-1].scenario
        sim = Simulator(last)
        for _ in range(10):
            sim.world.step()
            for cam in last.cameras:
                rows.extend(sim.backend.observe(sim.world, cam))
        builder = from_camera_rows(rows, resolution=last.cameras[0].capture.res)
        builder.write(out_dir / "coco.json")
        result.record("coco", {"images": len(builder.images),
                               "annotations": len(builder.annotations),
                               "usable_fraction": builder.usable_fraction(),
                               "difficulty": builder.difficulty_buckets()})
    except Exception as exc:  # noqa: BLE001
        result.fail("coco", exc)

    # ---- 4. degradation + realism scoring
    try:
        import cv2

        from .eval.realism_targets import score_profile
        from survsim.sensors.degrade import apply_profile

        render = _synthetic_render()
        scores = {}
        for profile in ("cctv_day_720p", "cctv_legacy_sd", "cctv_night_ir"):
            degraded = [apply_profile(render, profile, seed=k) for k in range(2)]
            cv2.imwrite(str(out_dir / f"sample_{profile}.jpg"), degraded[0],
                        [cv2.IMWRITE_JPEG_QUALITY, 90])
            scores[profile] = score_profile(degraded, profile)["score"]
        result.record("realism", scores)
    except Exception as exc:  # noqa: BLE001
        result.fail("realism", exc)

    # ---- 5. behaviour model on the generated data
    try:
        segments = segments_from_world(world, window_s=25.0, step_s=10.0)
        for s in segments:
            s.hard_negative = "commute_wait" in s.label
        train, test = split_by_identity(segments, test_fraction=0.3, seed=seed + 1)
        if not train or not test:
            raise ValueError("not enough identities to split")

        x = np.stack([extract_features(s) for s in train])
        y = np.array([s.is_suspicious for s in train], dtype=float)
        model = BehaviourClassifier().fit(x, y)
        scored = evaluate_classifier(model, test, camera_hours=camera_hours)
        result.record("behaviour", {
            "segments": len(segments), "train": len(train), "test": len(test),
            "auc": scored["auc"], "precision": scored["precision"],
            "recall": scored["recall"],
            "degenerate": scored.get("degenerate", False),
            "degenerate_reason": scored.get("degenerate_reason"),
            "top_features": list(model.importance().items())[:3],
        })
    except Exception as exc:  # noqa: BLE001
        result.fail("behaviour", exc)
        return _finish(result, out_dir)

    # ---- 6. alarm architecture: does verification rescue the detector?
    try:
        probs = model.predict_proba(np.stack([extract_features(s) for s in test]))
        candidates = [
            Candidate(t=s.t_start, uid=s.uid, label="suspicious.loiter",
                      confidence=float(p), zone="zone.gate",
                      corroborating={"rf": 0.9 if s.is_suspicious and i % 3 else 0.1})
            for i, (s, p) in enumerate(zip(test, probs))
        ]
        truth, seen = [], set()
        for s in sorted((s for s in test if s.is_suspicious), key=lambda s: s.t_start):
            if s.uid not in seen:
                truth.append(TruthEvent(s.t_start, s.t_end, "suspicious.loiter"))
                seen.add(s.uid)

        comparison = compare_architectures(
            candidates, truth, camera_hours=camera_hours, tolerance_s=40.0,
            variants={
                "raw": AlarmPipeline(threshold=0.5, persistence_windows=1),
                "verified": AlarmPipeline(threshold=0.8, persistence_windows=2,
                                          persistence_span_s=60,
                                          require_corroboration=True),
            })
        result.record("alarms", {
            name: {k: v[k] for k in
                   ("alarms", "precision", "recall", "false_alarms_per_camera_hour")}
            for name, v in comparison.items()
        })
    except Exception as exc:  # noqa: BLE001
        result.fail("alarms", exc)

    return _finish(result, out_dir)


def _finish(result: DemoResult, out_dir: Path) -> DemoResult:
    (out_dir / "demo_report.json").write_text(json.dumps(result.as_dict(), indent=2,
                                                         default=str))
    return result


def _synthetic_render(size: int = 320) -> np.ndarray:
    """A stand-in clean render for the degradation stage when no engine frame exists."""
    yy, xx = np.mgrid[0:size, 0:size].astype(np.float32)
    base = 95 + 45 * np.sin(xx / 55.0) + 28 * np.cos(yy / 65.0)
    img = np.dstack([base, base * 0.94 + 12, base * 0.88 + 20])
    return np.clip(img, 0, 255).astype(np.uint8)
