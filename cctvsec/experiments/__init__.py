"""Hypothesis-driven experiments: `survsim experiment <name>`.

Each experiment is a YAML config in `configs/` (hypothesis, seed, budget,
arms) plus a runner module. A run writes `<out>/results.json` (config,
environment, every number) and `<out>/row.md` (the markdown table that goes
into docs/research/32_EXPERIMENTS_LOG.md). Numbers in the log are copied
from those files, never typed by hand.
"""
from __future__ import annotations

import json
import platform
import time
from pathlib import Path
from typing import Any

import yaml

CONFIG_DIR = Path(__file__).parent / "configs"

# name -> (module, runner kind)
RUNNERS = {"reid_assoc": "reid_assoc", "detection": "detection", "farfield": "farfield", "reid": "reid", "alarms": "alarms",
           "diagnose": "diagnose", "farreal": "farreal",
           "tracking": "tracking", "reid_epochs": "reid_epochs", "night": "night",
           "alarm_scale": "alarm_scale", "realism_transfer": "realism_transfer", "dose": "dose",
           "rebaseline": "rebaseline", "tracking_transfer": "tracking_transfer",
           "reid_train": "reid_train", "operator_queue": "operator_queue",
           "label_noise": "label_noise", "dose_fixedstep": "dose_fixedstep", "conformal_theta": "conformal_theta",
           "night_profiles": "night_profiles", "quant_export": "quant_export",
           "autocalib": "autocalib", "drift_monitor": "drift_monitor", "line_cross": "line_cross",
           "theta_policy": "theta_policy", "sensor_fusion": "sensor_fusion",
           "evasion": "evasion", "ptz_slew": "ptz_slew",   # H47: staged CLI (`python -m cctvsec.experiments.evasion build|render|score`)
           "h46_reid_w_sweep": "h46_reid_w_sweep", "h46_reid_w_night_b": "h46_reid_w_night_b",
           "forensic_search": "forensic_search", "decoy_flooding": "decoy_flooding",
           "patrol_timing": "patrol_timing",
           "site_generalisation": "site_generalisation", "alarm_budget_scale": "alarm_budget_scale",
           "drift_monitor_scale": "drift_monitor_scale",
           "tracker_config_transfer": "tracker_config_transfer",
           "far_field_cc0": "far_field_cc0", "far_field_h3c": "far_field_h3c",
           "tile_merge": "tile_merge", "tile_merge_real": "tile_merge_real",
           "degrade_ablation_far": "degrade_ablation_far", "noise_recalibration": "noise_recalibration",
           "night_noise_check": "night_noise_check", "night_stage_ablation": "night_stage_ablation",
           "night_profile_fit": "night_profile_fit"}
ARM_RUNNERS = {"detection", "farreal", "dose_fixedstep"}   # runners that take --arm


def available() -> list[str]:
    return sorted(p.stem for p in CONFIG_DIR.glob("*.yaml"))


def load_config(name_or_path: str) -> dict[str, Any]:
    p = Path(name_or_path)
    if not p.is_file():
        p = CONFIG_DIR / f"{name_or_path}.yaml"
    if not p.is_file():
        raise FileNotFoundError(f"no experiment config {name_or_path!r}; have {available()}")
    cfg = yaml.safe_load(p.read_text())
    cfg.setdefault("name", p.stem)
    cfg["_config_path"] = str(p)
    return cfg


def _env() -> dict[str, Any]:
    env: dict[str, Any] = {"python": platform.python_version(), "host": platform.node()}
    try:
        import torch
        env["torch"] = torch.__version__
        if torch.cuda.is_available():
            env["gpu"] = torch.cuda.get_device_name(0)
            free, total = torch.cuda.mem_get_info()
            env["gpu_free_mib_at_start"] = free // 2**20
            env["gpu_total_mib"] = total // 2**20
    except Exception:  # noqa: BLE001, S110 - optional env info
        pass
    try:
        import ultralytics
        env["ultralytics"] = ultralytics.__version__
    except Exception:  # noqa: BLE001, S110 - optional env info
        pass
    return env


def seed_everything(seed: int) -> None:
    import random

    import numpy as np
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
    except Exception:  # noqa: BLE001, S110 - optional env info
        pass


def run_experiment(name: str, out: Path | None = None, arms: list[str] | None = None,
                   overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    import importlib

    cfg = load_config(name)
    cfg.update(overrides or {})
    out = Path(out or Path("out/experiments") / cfg["name"])
    out.mkdir(parents=True, exist_ok=True)
    seed_everything(int(cfg.get("seed", 0)))
    mod = importlib.import_module(f".{RUNNERS[cfg['runner']]}", __name__)
    t0 = time.time()
    body = mod.run(cfg, out, arms) if cfg["runner"] in ARM_RUNNERS else mod.run(cfg, out)
    res = {"experiment": cfg["name"], "hypothesis": cfg.get("hypothesis", ""),
           "config": {k: v for k, v in cfg.items() if not k.startswith("_")},
           "config_path": cfg["_config_path"], "env": _env(),
           "finished": time.strftime("%Y-%m-%d %H:%M:%S"),
           "wall_seconds_this_invocation": round(time.time() - t0, 1), **body}
    (out / "results.json").write_text(json.dumps(res, indent=1, default=str))
    (out / "row.md").write_text(f"### {cfg['name']}\n\n{cfg.get('hypothesis', '').strip()}\n\n"
                                + mod.markdown_rows(body, cfg))
    return res
