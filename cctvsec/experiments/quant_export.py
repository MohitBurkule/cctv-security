"""H38: accuracy cost of FP16 / INT8 export of the h14b detector (docs/research/66 H38,
pre-registered in docs/research/32).

For each h14b mixed-data checkpoint: FP32 PyTorch on CPU (control), ONNX FP32,
ONNX FP16 (onnxruntime float16 converter, FP32 IO) and two static INT8 QDQ models
(onnxruntime `quantize_static`, MinMax) calibrated on 100 real MOT20-01 frames or
on 100 synthetic batch_v8 frames. Every arm is scored through ultralytics predict
(same letterbox, NMS, conf) and the h14b/H25 MOT20-02 AP harness (`eval_det`).
CPU only. Latency is CPU context, not a Jetson number.
"""
from __future__ import annotations

import json
import random
import shutil
import time
from pathlib import Path
from typing import Any

import numpy as np

from .common import rpath, write_json

ARMS = ("fp32_torch", "onnx_fp32", "onnx_fp16", "int8_real", "int8_syn")


# ------------------------------------------------------------------ pure core

def evenly_spaced(items: list, n: int) -> list:
    """n items spread evenly over `items` (all of them if fewer)."""
    if len(items) <= n:
        return list(items)
    idx = np.linspace(0, len(items) - 1, n).round().astype(int)
    return [items[i] for i in idx]


def head_decode_nodes(nodes: list[tuple[str, str]], head: str = "/model.22/") -> list[str]:
    """Names of the Detect head's decode ops (everything in the head that is not a Conv and
    not inside the cv2/cv3 conv branches): DFL softmax, dist2bbox, sigmoid, concats."""
    return [n for n, op in nodes if n.startswith(head) and op != "Conv"
            and not n.startswith(head + "cv")]


def paired_summary(control: list[float], arm: list[float], n_boot: int = 10000,
                   seed: int = 0) -> dict[str, Any]:
    """loss = control - arm per checkpoint; mean, percentile bootstrap 95 % CI, range."""
    d = np.asarray(control, float) - np.asarray(arm, float)
    rng = np.random.default_rng(seed)
    bs = d[rng.integers(0, len(d), (n_boot, len(d)))].mean(1)
    return {"loss": [round(float(x), 4) for x in d], "mean": round(float(d.mean()), 4),
            "ci95": [round(float(np.percentile(bs, 2.5)), 4), round(float(np.percentile(bs, 97.5)), 4)],
            "min": round(float(d.min()), 4), "max": round(float(d.max()), 4)}


def decide(ap: dict[str, list[float]], cfg: dict[str, Any]) -> dict[str, Any]:
    th = cfg["thresholds"]
    san = [abs(a - b) for a, b in zip(ap["fp32_torch"], ap["onnx_fp32"])]
    sane = max(san) <= th["sanity"]
    ref = "fp32_torch" if sane else "onnx_fp32"
    loss = {a: paired_summary(ap[ref], ap[a]) for a in ARMS if a != ref}
    calib = paired_summary(ap["int8_real"], ap["int8_syn"])   # = AP(real) - AP(syn)
    return {"reference": ref, "sanity_max_abs": round(max(san), 4), "sanity_ok": sane,
            "loss_vs_reference": loss, "calib_gap_real_minus_syn": calib,
            "fp16_met": all(x <= th["fp16"] for x in loss["onnx_fp16"]["loss"]),
            "int8_met": all(x <= th["int8"] for x in loss["int8_real"]["loss"]),
            "calib_met": all(x >= th["calib_gap"] for x in calib["loss"])}


# ------------------------------------------------------------------ engine side

def _letterbox(path: str, shape) -> np.ndarray:
    import cv2
    from ultralytics.data.augment import LetterBox
    im = LetterBox(new_shape=tuple(shape), auto=False, stride=32)(image=cv2.imread(path))
    return (im[..., ::-1].transpose(2, 0, 1)[None].astype(np.float32) / 255.0).copy()


def calib_frames(cfg: dict[str, Any], kind: str) -> list[str]:
    c = cfg["calibration"][kind]
    if kind == "real":
        d = rpath(c["dir"])
        fr = sorted(p for p in d.glob("*.jpg") if c["first"] <= int(p.stem) <= c["last"])
        return [str(p) for p in evenly_spaced(fr, c["n"])]
    root = rpath(c["batch_dir"])
    pools = {}
    for sub in c["subdirs"]:
        pools[sub] = sorted(str(p) for p in root.glob(f"*/{sub}/*/*.png")
                            if not p.relative_to(root).parts[0].startswith("_"))
    rng = random.Random(c["seed"])
    per = c["n"] // len(pools)
    return [p for sub in c["subdirs"] for p in rng.sample(pools[sub], per)]


def export_arms(pt: Path, work: Path, cfg: dict[str, Any], calib: dict[str, list[str]]) -> dict[str, str]:
    import onnx
    from onnxruntime.quantization import (
        CalibrationDataReader,
        CalibrationMethod,
        QuantFormat,
        QuantType,
        quantize_static,
    )
    from onnxruntime.transformers.float16 import convert_float_to_float16
    from ultralytics import YOLO

    shape = cfg["input_shape"]
    work.mkdir(parents=True, exist_ok=True)
    local = work / "model.pt"
    shutil.copy(pt, local)
    f32 = work / "model_fp32.onnx"
    if not f32.is_file():
        f = YOLO(str(local)).export(format="onnx", imgsz=list(shape), device="cpu", simplify=True,
                                    dynamic=False, half=False)
        Path(f).rename(f32)
    out = {"fp32_torch": str(local), "onnx_fp32": str(f32)}
    f16 = work / "model_fp16.onnx"
    if not f16.is_file():
        onnx.save(convert_float_to_float16(onnx.load(str(f32)), keep_io_types=True), str(f16))
    out["onnx_fp16"] = str(f16)
    m = onnx.load(str(f32))
    excl = head_decode_nodes([(n.name, n.op_type) for n in m.graph.node])
    inp = m.graph.input[0].name

    class Reader(CalibrationDataReader):
        def __init__(self, paths):
            self.it = iter(paths)

        def get_next(self):
            p = next(self.it, None)
            return None if p is None else {inp: _letterbox(p, shape)}

    for kind in ("real", "syn"):
        q = work / f"model_int8_{kind}.onnx"
        if not q.is_file():
            quantize_static(str(f32), str(q), Reader(calib[kind]), quant_format=QuantFormat.QDQ,
                            per_channel=True, weight_type=QuantType.QInt8,
                            activation_type=QuantType.QInt8,
                            calibrate_method=CalibrationMethod.MinMax, nodes_to_exclude=excl)
        out[f"int8_{kind}"] = str(q)
    out["_excluded_nodes"] = excl
    return out


def detect_cpu(m: dict[str, Any], weights: str, imgsz: int, batch: int = 8):
    from ultralytics import YOLO

    from ..baselines.run import DET_CONF, _abs, _sequences
    net = YOLO(weights, task="detect")
    res: dict[str, dict[int, list[dict]]] = {}
    for run, cam, c in _sequences(m):
        frames = sorted(c["frames"], key=int)
        per = {}
        b = 1 if weights.endswith(".onnx") else batch   # static batch-1 ONNX
        for i in range(0, len(frames), b):
            chunk = frames[i:i + b]
            preds = net.predict([_abs(m["_root"], c["frames"][f]) for f in chunk], classes=[0],
                                conf=DET_CONF, imgsz=imgsz, verbose=False, half=False,
                                max_det=1000, device="cpu")
            for f, p in zip(chunk, preds):
                xyxy = p.boxes.xyxy.cpu().numpy()
                sc = p.boxes.conf.cpu().numpy()
                per[int(f)] = [{"bbox": [float(a), float(y0), float(x - a), float(y - y0)], "score": float(s)}
                               for (a, y0, x, y), s in zip(xyxy, sc)]
        res[f"{run['name']}/{cam}"] = per
    return res


def latency_ms(weights: str, shape, frames: list[str], n: int, warm: int) -> float:
    xs = [_letterbox(p, shape) for p in frames[:n]]
    if weights.endswith(".onnx"):
        import onnxruntime as ort
        s = ort.InferenceSession(weights, providers=["CPUExecutionProvider"])
        name = s.get_inputs()[0].name
        fn = lambda x: s.run(None, {name: x})
    else:
        import torch
        from ultralytics import YOLO
        net = YOLO(weights).model.float().eval()

        def fn(x):
            with torch.inference_mode():
                return net(torch.from_numpy(x))
    for x in xs[:warm]:
        fn(x)
    ts = []
    for x in xs:
        t = time.perf_counter()
        fn(x)
        ts.append((time.perf_counter() - t) * 1000)
    return round(float(np.median(ts)), 2)


def run(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    if cfg.get("mode") == "h43":
        return run_h43(cfg, out)
    if cfg.get("mode") == "h43c":
        return run_h43c(cfg, out)
    if cfg.get("mode") == "h43d":
        return run_h43d(cfg, out)
    from ..baselines.run import eval_det
    from survsim.datasets.build import load_manifest
    from .detection import _eval_manifests

    m = load_manifest(_eval_manifests(cfg, out)["mot20_02"])
    calib = {k: calib_frames(cfg, k) for k in ("real", "syn")}
    write_json(out / "calibration_frames.json", calib)
    eval_frames = [str(Path(m["_root"]) / v) if not Path(v).is_absolute() else v
                   for r in m["runs"] for c in r["cameras"].values() for v in c["frames"].values()]
    ckpts = {}
    for name in cfg["checkpoints"]:
        cp = out / "ckpts" / f"{name}.json"
        if cp.is_file():
            ckpts[name] = json.loads(cp.read_text())
            continue
        work = out / "work" / name
        paths = export_arms(rpath(cfg["checkpoint_glob"].format(name=name)), work, cfg, calib)
        rec: dict[str, Any] = {"excluded_nodes": paths.pop("_excluded_nodes"), "arms": {}}
        for arm in ARMS:
            t0 = time.time()
            dets = detect_cpu(m, paths[arm], cfg["eval_imgsz"])
            det = eval_det(m, dets)
            rec["arms"][arm] = {
                "AP": round(det["all"]["AP"], 4), "AP50": round(det["all"]["AP50"], 4),
                "AP75": round(det["all"]["AP75"], 4), "eval_seconds": round(time.time() - t0, 1),
                "cpu_latency_ms_median": latency_ms(paths[arm], cfg["input_shape"], eval_frames,
                                                    cfg["latency"]["n"], cfg["latency"]["warmup"]),
                "file_mib": round(Path(paths[arm]).stat().st_size / 2**20, 2)}
            print(name, arm, rec["arms"][arm], flush=True)
        write_json(cp, rec)
        ckpts[name] = rec
    ap = {a: [ckpts[c]["arms"][a]["AP"] for c in cfg["checkpoints"]] for a in ARMS}
    return {"checkpoints": ckpts, "ap": ap,
            "ap_mean": {a: round(float(np.mean(v)), 4) for a, v in ap.items()},
            "latency_ms_mean": {a: round(float(np.mean([ckpts[c]["arms"][a]["cpu_latency_ms_median"]
                                                        for c in cfg["checkpoints"]])), 2) for a in ARMS},
            "decision": decide(ap, cfg)}


def markdown_rows(res: dict[str, Any], cfg: dict[str, Any]) -> str:
    if cfg.get("mode") == "h43":
        return markdown_rows_h43(res)
    if cfg.get("mode") == "h43c":
        return markdown_rows_h43c(res)
    if cfg.get("mode") == "h43d":
        return markdown_rows_h43c(res)
    d = res["decision"]
    lines = ["| arm | AP per checkpoint | AP mean | loss vs ref mean [95 % boot] (range) | CPU ms/im | MiB |",
             "|---|---|---|---|---|---|"]
    c0 = cfg["checkpoints"][0]
    for a in ARMS:
        ls = d["loss_vs_reference"].get(a)
        lt = (f"{ls['mean']:+.4f} [{ls['ci95'][0]:+.4f}, {ls['ci95'][1]:+.4f}] "
              f"({ls['min']:+.4f}..{ls['max']:+.4f})") if ls else "reference"
        lines.append(f"| {a} | {' / '.join(f'{x:.4f}' for x in res['ap'][a])} | {res['ap_mean'][a]:.4f} | "
                     f"{lt} | {res['latency_ms_mean'][a]} | "
                     f"{res['checkpoints'][c0]['arms'][a]['file_mib']} |")
    cg = d["calib_gap_real_minus_syn"]
    lines += ["", (f"reference: {d['reference']} (sanity max |ONNX-FP32 − torch| = {d['sanity_max_abs']}); "
              f"INT8 real − syn AP {cg['mean']:+.4f} [{cg['ci95'][0]:+.4f}, {cg['ci95'][1]:+.4f}]; "
              f"FP16 met: {d['fp16_met']}; INT8 met: {d['int8_met']}; calibration gap met: {d['calib_met']}")]
    return "\n".join(lines) + "\n"


# ================================================================== H43: calibration + QAT
# docs/research/66 H43, pre-registered in 32. Same file so the H38 path stays untouched: the
# H43 config sets `mode: h43`, and `run` dispatches on it.

H43_ARMS = ("fp32_torch", "int8_minmax", "int8_percentile", "int8_entropy", "qat_fp32", "int8_qat")
H43_INT8 = ("int8_minmax", "int8_percentile", "int8_entropy", "int8_qat")


def recovery(minmax_loss: float, arm_loss: float) -> float:
    """Fraction of the MinMax-PTQ loss an arm recovers (1 = back to FP32, 0 = no better, <0 worse)."""
    if minmax_loss <= 0:
        return float("nan")
    return (minmax_loss - arm_loss) / minmax_loss


def decide_h43(m: dict[str, dict[str, list[float]]], cfg: dict[str, Any]) -> dict[str, Any]:
    """m[metric][arm] = per-checkpoint values, metric in AP/AP50/AP75."""
    th = cfg["thresholds"]
    loss = {met: {a: paired_summary(m[met]["fp32_torch"], m[met][a], seed=cfg.get("seed", 0))
                  for a in H43_ARMS if a != "fp32_torch"} for met in ("AP", "AP50", "AP75")}
    rec = {met: {a: round(recovery(loss[met]["int8_minmax"]["mean"], loss[met][a]["mean"]), 3)
                 for a in ("int8_percentile", "int8_entropy", "int8_qat")} for met in ("AP", "AP75")}
    return {"loss_vs_fp32": loss, "recovery": rec,
            "ptq_met": rec["AP75"]["int8_percentile"] >= th["ptq_recovery"],
            "ptq_secondary_only": (rec["AP75"]["int8_percentile"] < th["ptq_recovery"]
                                   <= rec["AP75"]["int8_entropy"]),
            "qat_recovery_met": rec["AP75"]["int8_qat"] >= th["qat_recovery"],
            "qat_every_ckpt_met": all(x <= th["qat_ap_loss"] for x in loss["AP"]["int8_qat"]["loss"]),
            "qat_met": (rec["AP75"]["int8_qat"] >= th["qat_recovery"]
                        and all(x <= th["qat_ap_loss"] for x in loss["AP"]["int8_qat"]["loss"]))}


def _fq_attach(model):
    """Attach fake-quant to a BN-fused ultralytics model: per-channel symmetric S8 weights on every
    Conv2d (parametrisation), 8-bit affine activations at every Conv2d input and every ultralytics
    Conv module output (post-SiLU). Returns a detach() callable that removes all of it and leaves the
    trained float weights in place."""
    import torch
    import torch.nn.utils.parametrize as P
    from torch.ao.quantization import (
        FakeQuantize,
        MovingAverageMinMaxObserver,
        MovingAveragePerChannelMinMaxObserver,
    )
    from ultralytics.nn.modules import Conv

    def act_fq():
        return FakeQuantize(MovingAverageMinMaxObserver, quant_min=0, quant_max=255,
                            dtype=torch.quint8, qscheme=torch.per_tensor_affine)

    class WFQ(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.fq = FakeQuantize(MovingAveragePerChannelMinMaxObserver, quant_min=-127, quant_max=127,
                                   dtype=torch.qint8, qscheme=torch.per_channel_symmetric, ch_axis=0)

        def forward(self, w):
            return self.fq(w)

    handles, convs = [], []
    dev = next(model.parameters()).device
    for mod in model.modules():
        if isinstance(mod, torch.nn.Conv2d):
            P.register_parametrization(mod, "weight", WFQ().to(mod.weight.device))
            mod.fq_in = act_fq().to(mod.weight.device)
            handles.append(mod.register_forward_pre_hook(lambda m, a: (m.fq_in(a[0]),)))
            convs.append(mod)
        elif isinstance(mod, Conv):
            mod.fq_out = act_fq().to(dev)
            handles.append(mod.register_forward_hook(lambda m, a, o: m.fq_out(o)))

    def detach():
        for h in handles:
            h.remove()
        for mod in list(model.modules()):
            if isinstance(mod, torch.nn.Conv2d) and P.is_parametrized(mod, "weight"):
                P.remove_parametrizations(mod, "weight", leave_parametrized=False)
            for a in ("fq_in", "fq_out"):
                if hasattr(mod, a):
                    delattr(mod, a)
    return detach


def qat_finetune(pt: Path, data_yaml: Path, out_pt: Path, q: dict[str, Any], seed: int) -> dict[str, Any]:
    """Fine-tune `pt` with fake-quant for q['iters'] steps (AdamW, constant q['lr']); save a normal
    ultralytics checkpoint (fake-quant stripped, BN already fused) to out_pt."""
    import copy

    import torch
    from ultralytics import YOLO
    from ultralytics.cfg import get_cfg
    from ultralytics.data import build_dataloader, build_yolo_dataset
    from ultralytics.data.utils import check_det_dataset

    torch.manual_seed(seed)
    random.seed(seed)
    np.random.seed(seed)
    dev = q.get("device", "cuda:0" if torch.cuda.is_available() else "cpu")
    model = YOLO(str(pt)).model.float().fuse(verbose=False).to(dev)
    for p in model.parameters():
        p.requires_grad_(True)
    args = get_cfg(overrides={"imgsz": q["imgsz"], "batch": q["batch"], "workers": q["workers"],
                              "seed": seed, "close_mosaic": 0})
    model.args = args
    data = check_det_dataset(str(data_yaml))
    ds = build_yolo_dataset(args, data["train"], q["batch"], data, mode="train", stride=32)
    dl = build_dataloader(ds, q["batch"], q["workers"], shuffle=True, rank=-1)
    detach = _fq_attach(model)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=q["lr"],
                            betas=(0.9, 0.999), weight_decay=q["weight_decay"])
    model.train()
    losses, it, t0 = [], 0, time.time()
    while it < q["iters"]:
        for b in dl:
            b["img"] = b["img"].to(dev).float() / 255
            for k in ("batch_idx", "cls", "bboxes"):
                b[k] = b[k].to(dev)
            loss, items = model.loss(b)
            opt.zero_grad()
            loss.sum().backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 10.0)
            opt.step()
            it_ = items.values() if isinstance(items, dict) else items
            losses.append([round(float(x), 4) for x in (v.detach().cpu() for v in it_)])
            it += 1
            if it >= q["iters"]:
                break
    detach()
    model.eval()
    ck = torch.load(str(pt), map_location="cpu", weights_only=False)
    ck["model"] = copy.deepcopy(model).cpu().half()
    ck["ema"] = None
    ck["optimizer"] = None
    out_pt.parent.mkdir(parents=True, exist_ok=True)
    torch.save(ck, str(out_pt))
    del model
    torch.cuda.empty_cache()
    return {"iters": it, "seconds": round(time.time() - t0, 1), "loss_first": losses[0],
            "loss_last10_mean": [round(float(x), 4) for x in np.mean(losses[-10:], 0)]}


def _onnx_fp32(pt: Path, dst: Path, shape) -> Path:
    from ultralytics import YOLO
    if not dst.is_file():
        f = YOLO(str(pt)).export(format="onnx", imgsz=list(shape), device="cpu", simplify=True,
                                 dynamic=False, half=False)
        Path(f).rename(dst)
    return dst


def _int8(f32: Path, dst: Path, frames: list[str], shape, method: str,
          extra: dict[str, Any] | None = None) -> Path:
    import onnx
    from onnxruntime.quantization import (
        CalibrationDataReader,
        CalibrationMethod,
        QuantFormat,
        QuantType,
        quantize_static,
    )
    if dst.is_file():
        return dst
    m = onnx.load(str(f32))
    excl = head_decode_nodes([(n.name, n.op_type) for n in m.graph.node])
    inp = m.graph.input[0].name

    class Reader(CalibrationDataReader):
        def __init__(self, paths):
            self.it = iter(paths)

        def get_next(self):
            p = next(self.it, None)
            return None if p is None else {inp: _letterbox(p, shape)}

    quantize_static(str(f32), str(dst), Reader(frames), quant_format=QuantFormat.QDQ,
                    per_channel=True, weight_type=QuantType.QInt8, activation_type=QuantType.QInt8,
                    calibrate_method=getattr(CalibrationMethod, method), nodes_to_exclude=excl,
                    # chunked histogram collection keeps RAM bounded; 100 % 7 != 0 because ORT 1.30
                    # raises "No data is collected" when the final chunk is empty
                    extra_options={"CalibMaxIntermediateOutputs": 7, **(extra or {})})
    return dst


def h43_one(cfg: dict[str, Any], out: Path, name: str, only: str = "all") -> dict[str, Any]:
    """Everything for one checkpoint; cached in out/ckpts/<name>.json. only='qat' trains and stops."""
    from ..baselines.run import eval_det
    from survsim.datasets.build import load_manifest
    from .detection import _eval_manifests

    ck = cfg["checkpoints"][name]
    cp = out / "ckpts" / f"{name}.json"
    rec = json.loads(cp.read_text()) if cp.is_file() else {"arms": {}, "source": ck}
    work = out / "work" / name
    work.mkdir(parents=True, exist_ok=True)
    shape = cfg["input_shape"]
    pt = work / "model.pt"          # local copy: ultralytics export writes next to the .pt
    if not pt.is_file():
        shutil.copy(rpath(ck["pt"]), pt)
    qpt = work / "qat.pt"
    if not qpt.is_file():
        rec["qat"] = qat_finetune(rpath(ck["pt"]), rpath(ck["data"]), qpt, cfg["qat"], cfg["seed"])
        write_json(cp, rec)
    if only == "qat":
        return rec
    frames = json.loads((out / "calibration_frames.json").read_text())["real"]
    f32 = _onnx_fp32(pt, work / "model_fp32.onnx", shape)
    q32 = _onnx_fp32(qpt, work / "qat_fp32.onnx", shape)
    c = cfg["calibration"]
    paths = {"fp32_torch": str(pt),
             "int8_minmax": str(_int8(f32, work / "int8_minmax.onnx", frames, shape, "MinMax")),
             "int8_percentile": str(_int8(f32, work / "int8_percentile.onnx", frames, shape, "Percentile",
                                          {"CalibPercentile": c["percentile"]})),
             "int8_entropy": str(_int8(f32, work / "int8_entropy.onnx", frames, shape, "Entropy")),
             "qat_fp32": str(q32),
             "int8_qat": str(_int8(q32, work / "int8_qat.onnx", frames, shape, "MinMax"))}
    reuse = {}
    if ck.get("reuse_h38"):
        h = json.loads(rpath(ck["reuse_h38"]).read_text())["arms"]
        reuse = {"fp32_torch": h["fp32_torch"], "int8_minmax": h["int8_real"]}
    m = load_manifest(_eval_manifests(cfg, out)["mot20_02"])
    eval_frames = [str(Path(m["_root"]) / v) for r in m["runs"] for cc in r["cameras"].values()
                   for v in cc["frames"].values()]
    for arm in H43_ARMS:
        if arm in rec["arms"]:
            continue
        if arm in reuse:
            rec["arms"][arm] = {**{k: reuse[arm][k] for k in ("AP", "AP50", "AP75")},
                                "reused_from": ck["reuse_h38"]}
        else:
            t0 = time.time()
            det = eval_det(m, detect_cpu(m, paths[arm], cfg["eval_imgsz"]))
            rec["arms"][arm] = {
                "AP": round(det["all"]["AP"], 4), "AP50": round(det["all"]["AP50"], 4),
                "AP75": round(det["all"]["AP75"], 4), "eval_seconds": round(time.time() - t0, 1),
                "cpu_latency_ms_median": latency_ms(paths[arm], shape, eval_frames,
                                                    cfg["latency"]["n"], cfg["latency"]["warmup"]),
                "file_mib": round(Path(paths[arm]).stat().st_size / 2**20, 2)}
        print(name, arm, rec["arms"][arm], flush=True)
        write_json(cp, rec)
    return rec


def run_h43(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    cf = out / "calibration_frames.json"
    if not cf.is_file():
        write_json(cf, {"real": calib_frames(cfg, "real")})
    names = list(cfg["checkpoints"])
    ck = {n: h43_one(cfg, out, n) for n in names}
    mets = {met: {a: [ck[n]["arms"][a][met] for n in names] for a in H43_ARMS}
            for met in ("AP", "AP50", "AP75")}
    h14 = [n for n in names if cfg["checkpoints"][n].get("reuse_h38")]
    sub = {met: {a: [ck[n]["arms"][a][met] for n in h14] for a in H43_ARMS} for met in mets}
    return {"checkpoints": ck, "metrics": mets,
            "mean": {met: {a: round(float(np.mean(v)), 4) for a, v in d.items()} for met, d in mets.items()},
            "decision": decide_h43(mets, cfg),
            "decision_h14b_only": decide_h43(sub, cfg) if len(h14) >= 2 else None}


def markdown_rows_h43(res: dict[str, Any]) -> str:
    d = res["decision"]
    lines = ["| arm | AP mean | AP loss [95 % boot] (range) | AP75 loss [95 % boot] | AP50 loss | AP75 recovery |",
             "|---|---|---|---|---|---|"]
    for a in H43_ARMS:
        if a == "fp32_torch":
            lines.append(f"| {a} | {res['mean']['AP'][a]:.4f} | reference | | | |")
            continue
        L = {k: d["loss_vs_fp32"][k][a] for k in ("AP", "AP50", "AP75")}
        r = d["recovery"]["AP75"].get(a, "")
        lines.append(f"| {a} | {res['mean']['AP'][a]:.4f} | {L['AP']['mean']:+.4f} [{L['AP']['ci95'][0]:+.4f}, "
                     f"{L['AP']['ci95'][1]:+.4f}] ({L['AP']['min']:+.4f}..{L['AP']['max']:+.4f}) | "
                     f"{L['AP75']['mean']:+.4f} [{L['AP75']['ci95'][0]:+.4f}, {L['AP75']['ci95'][1]:+.4f}] | "
                     f"{L['AP50']['mean']:+.4f} | {r} |")
    lines += ["", (f"PTQ met: {d['ptq_met']} (secondary only: {d['ptq_secondary_only']}); "
                   f"QAT met: {d['qat_met']} (recovery {d['qat_recovery_met']}, every-ckpt ≤ bar "
                   f"{d['qat_every_ckpt_met']})")]
    return "\n".join(lines) + "\n"


# ================================================================== H43c: QDQ from learned QAT ranges
# docs/research/66 H43c, pre-registered in 32. Root cause (H43b): int8_qat re-quantises the QAT model
# with a fresh MinMax pass over calibration frames, discarding the fake-quant observers' learned
# scale/zero-point. Here we re-attach fake-quant to the cached (already fine-tuned) qat.pt, run it in
# observer-only mode over the same calibration frames to read off the *converged* observer ranges, and
# hand those to onnxruntime `quantize_static` as `TensorQuantOverrides` so the QDQ graph is built from
# them instead of a fresh calibration pass. No re-fine-tuning; qat.pt / qat_fp32.onnx are reused from
# `h43_out`.

H43C_ARMS = ("fp32_torch", "int8_minmax", "qat_fp32", "int8_qat_qdq")


def _affine_qparams(minv: float, maxv: float, qmin: int = -128, qmax: int = 127) -> tuple[float, int]:
    """Standard affine int8 quant grid from an observed [minv, maxv] range (matches what onnxruntime's
    own MinMax calibration would compute for a QInt8 activation, just fed a different range)."""
    minv, maxv = min(0.0, minv), max(0.0, maxv)
    scale = max((maxv - minv) / (qmax - qmin), 1e-8)
    zp = round(qmin - minv / scale)
    return scale, max(qmin, min(qmax, zp))


def _collect_qat_ranges(qpt: Path, calib_frames: list[str], shape) -> dict[str, Any]:
    """Re-attach fake-quant to the fine-tuned qat.pt, run observer-only forward passes over the real
    calibration frames (CPU, no grad), and return per-Conv2d weight per-channel scales and activation
    input (scale, zero_point), in `model.modules()` Conv2d traversal order."""
    import torch
    from ultralytics import YOLO

    model = YOLO(str(qpt)).model.float().eval().to("cpu")
    detach = _fq_attach(model)
    fqs = [m for m in model.modules() if hasattr(m, "disable_fake_quant")]
    for fq in fqs:
        fq.disable_fake_quant()
        fq.enable_observer()
    with torch.inference_mode():
        for p in calib_frames:
            model(torch.from_numpy(_letterbox(p, shape)))
    convs = [m for m in model.modules() if isinstance(m, torch.nn.Conv2d)]
    weight_bytes, weight_scales, act_qparams = [], [], []
    for c in convs:
        raw = c.parametrizations.weight.original.detach().numpy().astype("float32")  # pre-fake-quant
        weight_bytes.append(raw.tobytes())    # weight: identical to what qat_fp32.onnx has as initializer
        wfq = c.parametrizations.weight[0].fq
        weight_scales.append([float(x) for x in wfq.scale.detach().reshape(-1).tolist()])
        obs = c.fq_in.activation_post_process
        act_qparams.append(_affine_qparams(float(obs.min_val), float(obs.max_val)))
    detach()
    return {"n_convs": len(convs), "weight_bytes": weight_bytes, "weight_scales": weight_scales,
            "act_qparams": act_qparams}


def _qdq_from_ranges(q32: Path, dst: Path, ranges: dict[str, Any], calib_frames: list[str],
                     shape) -> dict[str, Any]:
    """Build the INT8 QDQ graph for q32 using `ranges` (from `_collect_qat_ranges`) as
    `TensorQuantOverrides`, instead of a fresh calibration pass. Conv nodes in ONNX graph order are
    zipped 1:1 with Conv2d modules in PyTorch traversal order (both counts asserted equal)."""
    import onnx
    from onnx import numpy_helper
    from onnxruntime.quantization import (
        CalibrationDataReader,
        QuantFormat,
        QuantType,
        quantize_static,
    )

    m = onnx.load(str(q32))
    convs = [n for n in m.graph.node if n.op_type == "Conv"]
    if len(convs) != ranges["n_convs"]:
        raise RuntimeError(f"Conv count mismatch: onnx={len(convs)} torch={ranges['n_convs']} "
                           f"-- cannot map observer ranges to ONNX tensors for {q32}")
    # Map each ONNX Conv node to its PyTorch module by exact weight-tensor byte match, not position:
    # `model.modules()` traversal order (definition order) does not match the ONNX graph's forward
    # execution order for this branchy YOLO backbone (verified: 31/64 convs mismatched by position).
    # The pre-fake-quant weight values are bit-identical between the freshly-loaded torch model and
    # the qat_fp32.onnx initializer, so a byte-exact match is unambiguous (checked: 64/64 unique).
    inits = {i.name: numpy_helper.to_array(i) for i in m.graph.initializer}
    by_bytes = {b: i for i, b in enumerate(ranges["weight_bytes"])}
    excl = head_decode_nodes([(n.name, n.op_type) for n in m.graph.node])
    overrides: dict[str, list[dict[str, Any]]] = {}
    matched_weight_tensors, matched_act_tensors = [], []
    for node in convs:
        wname, aname = node.input[1], node.input[0]
        key = inits[wname].astype("float32").tobytes()
        if key not in by_bytes:
            raise RuntimeError(f"no torch Conv weight matches ONNX initializer {wname!r} in {q32}")
        idx = by_bytes[key]
        wscale, (ascale, azp) = ranges["weight_scales"][idx], ranges["act_qparams"][idx]
        overrides[wname] = [{"scale": np.array(s, dtype=np.float32), "zero_point": np.array(0, dtype=np.int8),
                            "axis": 0} for s in wscale]
        overrides[aname] = [{"scale": np.array(ascale, dtype=np.float32),
                            "zero_point": np.array(azp, dtype=np.int8), "quant_type": QuantType.QInt8}]
        matched_weight_tensors.append(wname)
        matched_act_tensors.append(aname)

    inp = m.graph.input[0].name

    class Reader(CalibrationDataReader):
        """Still fed real frames (ORT 1.30 requires >=1 calibration batch even with full tensor
        overrides), but every tensor we care about (`overrides`, above) ignores whatever this pass
        computes and uses the QAT observer's learned range instead."""

        def __init__(self, paths):
            self.it = iter(paths)

        def get_next(self):
            p = next(self.it, None)
            return None if p is None else {inp: _letterbox(p, shape)}

    quantize_static(str(q32), str(dst), Reader(calib_frames), quant_format=QuantFormat.QDQ, per_channel=True,
                    weight_type=QuantType.QInt8, activation_type=QuantType.QInt8, nodes_to_exclude=excl,
                    extra_options={"TensorQuantOverrides": overrides, "DedicatedQDQPair": True,
                                  "QDQDisableWeightAdjustForInt32Bias": True})
    return {"n_weight_tensors": len(matched_weight_tensors), "n_act_tensors": len(matched_act_tensors),
            "sample_weight_tensor": matched_weight_tensors[0], "sample_act_tensor": matched_act_tensors[0],
            "sample_weight_scale0": ranges["weight_scales"][0][0], "sample_act_qparams": ranges["act_qparams"][0]}


def verify_learned_ranges_carried(dst: Path, meta: dict[str, Any]) -> dict[str, Any]:
    """Load the exported QDQ graph and check the sample weight/activation scale initializers really
    carry the learned observer values passed in via `TensorQuantOverrides` (not a value MinMax would
    have picked independently). This is the regression check asked for in H43c."""
    import onnx
    from onnx import numpy_helper

    m = onnx.load(str(dst))
    inits = {i.name: numpy_helper.to_array(i) for i in m.graph.initializer}
    w_scale_name = meta["sample_weight_tensor"] + "_scale"
    checks = {}
    if w_scale_name in inits:
        got = float(np.asarray(inits[w_scale_name]).reshape(-1)[0])
        checks["weight_scale_match"] = abs(got - meta["sample_weight_scale0"]) < 1e-6
        checks["weight_scale_got"] = got
    a_scale_name = meta["sample_act_tensor"] + "_scale"
    if a_scale_name in inits:
        got = float(np.asarray(inits[a_scale_name]))
        want = meta["sample_act_qparams"][0]
        checks["act_scale_match"] = abs(got - want) < 1e-6
        checks["act_scale_got"] = got
    checks["ok"] = all(v for k, v in checks.items() if k.endswith("_match"))
    return checks


def h43c_one(cfg: dict[str, Any], out: Path, name: str) -> dict[str, Any]:
    from ..baselines.run import eval_det
    from survsim.datasets.build import load_manifest
    from .detection import _eval_manifests

    h43_out = rpath(cfg["h43_out"])
    cp = out / "ckpts" / f"{name}.json"
    rec = json.loads(cp.read_text()) if cp.is_file() else {"arms": {}, "source": cfg["checkpoints"][name]}
    work = h43_out / "work" / name          # reuse H43b's cached artefacts (no re-fine-tuning)
    shape = cfg["input_shape"]
    frames = json.loads((h43_out / "calibration_frames.json").read_text())["real"]

    if "verify" not in rec:
        ranges = _collect_qat_ranges(work / "qat.pt", frames, shape)
        dst = out / "work" / name / "int8_qat_qdq.onnx"
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.is_file():
            meta = _qdq_from_ranges(work / "qat_fp32.onnx", dst, ranges, frames, shape)
        else:
            meta = json.loads((dst.parent / "meta.json").read_text())
        write_json(dst.parent / "meta.json", meta)
        rec["verify"] = verify_learned_ranges_carried(dst, meta)
        write_json(cp, rec)

    h38 = json.loads(rpath(cfg["checkpoints"][name]["reuse_h38"]).read_text())["arms"] \
        if cfg["checkpoints"][name].get("reuse_h38") else None
    h43b = json.loads((h43_out / "ckpts" / f"{name}.json").read_text())["arms"]
    paths = {"fp32_torch": str(work / "model.pt"), "qat_fp32": str(work / "qat_fp32.onnx"),
             "int8_qat_qdq": str(out / "work" / name / "int8_qat_qdq.onnx")}
    m = load_manifest(_eval_manifests(cfg, out)["mot20_02"])
    eval_frames = [str(Path(m["_root"]) / v) for r in m["runs"] for cc in r["cameras"].values()
                   for v in cc["frames"].values()]
    for arm in H43C_ARMS:
        if arm in rec["arms"]:
            continue
        if arm in ("fp32_torch", "int8_minmax") and h38 is not None:
            src = h38["fp32_torch"] if arm == "fp32_torch" else h38["int8_real"]
            rec["arms"][arm] = {**{k: src[k] for k in ("AP", "AP50", "AP75")}, "reused_from": "h38"}
            continue
        if arm in ("fp32_torch", "qat_fp32", "int8_minmax") and arm in h43b:
            src = h43b[arm]
            rec["arms"][arm] = {**{k: src[k] for k in ("AP", "AP50", "AP75")}, "reused_from": "h43b"}
            continue
        t0 = time.time()
        det = eval_det(m, detect_cpu(m, paths[arm], cfg["eval_imgsz"]))
        rec["arms"][arm] = {
            "AP": round(det["all"]["AP"], 4), "AP50": round(det["all"]["AP50"], 4),
            "AP75": round(det["all"]["AP75"], 4), "eval_seconds": round(time.time() - t0, 1),
            "cpu_latency_ms_median": latency_ms(paths[arm], shape, eval_frames,
                                                cfg["latency"]["n"], cfg["latency"]["warmup"]),
            "file_mib": round(Path(paths[arm]).stat().st_size / 2**20, 2)}
        print(name, arm, rec["arms"][arm], flush=True)
        write_json(cp, rec)
    return rec


def decide_h43c(mets: dict[str, dict[str, list[float]]], cfg: dict[str, Any]) -> dict[str, Any]:
    th = cfg["thresholds"]
    loss = {met: {a: paired_summary(mets[met]["fp32_torch"], mets[met][a], seed=cfg.get("seed", 0))
                  for a in H43C_ARMS if a != "fp32_torch"} for met in ("AP", "AP50", "AP75")}
    rec = {met: round(recovery(loss[met]["int8_minmax"]["mean"], loss[met]["int8_qat_qdq"]["mean"]), 3)
           for met in ("AP", "AP75")}
    return {"loss_vs_fp32": loss, "recovery": rec,
            "qdq_recovery_met": rec["AP75"] >= th["qdq_recovery"],
            "qdq_recovery_secondary_only": (rec["AP75"] < th["qdq_recovery"] <= th["qdq_recovery_secondary"]
                                            or th["qdq_recovery_secondary"] <= rec["AP75"] < th["qdq_recovery"]),
            "qdq_every_ckpt_met": all(x <= th["qdq_ap_loss"] for x in loss["AP"]["int8_qat_qdq"]["loss"]),
            "qdq_met": (rec["AP75"] >= th["qdq_recovery"]
                       and all(x <= th["qdq_ap_loss"] for x in loss["AP"]["int8_qat_qdq"]["loss"]))}


def run_h43c(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    names = list(cfg["checkpoints"])
    ck = {n: h43c_one(cfg, out, n) for n in names}
    mets = {met: {a: [ck[n]["arms"][a][met] for n in names] for a in H43C_ARMS} for met in ("AP", "AP50", "AP75")}
    ranges_verified = {n: ck[n]["verify"].get("ok", False) for n in names}
    return {"checkpoints": ck, "metrics": mets, "ranges_verified": ranges_verified,
            "all_ranges_verified": all(ranges_verified.values()),
            "mean": {met: {a: round(float(np.mean(v)), 4) for a, v in d.items()} for met, d in mets.items()},
            "decision": decide_h43c(mets, cfg)}


def markdown_rows_h43c(res: dict[str, Any]) -> str:
    d = res["decision"]
    lines = ["| arm | AP mean | AP loss [95 % boot] (range) | AP75 loss [95 % boot] | AP50 loss |",
             "|---|---|---|---|---|"]
    for a in H43C_ARMS:
        if a == "fp32_torch":
            lines.append(f"| {a} | {res['mean']['AP'][a]:.4f} | reference | | |")
            continue
        L = {k: d["loss_vs_fp32"][k][a] for k in ("AP", "AP50", "AP75")}
        lines.append(f"| {a} | {res['mean']['AP'][a]:.4f} | {L['AP']['mean']:+.4f} [{L['AP']['ci95'][0]:+.4f}, "
                     f"{L['AP']['ci95'][1]:+.4f}] ({L['AP']['min']:+.4f}..{L['AP']['max']:+.4f}) | "
                     f"{L['AP75']['mean']:+.4f} [{L['AP75']['ci95'][0]:+.4f}, {L['AP75']['ci95'][1]:+.4f}] | "
                     f"{L['AP50']['mean']:+.4f} |")
    lines += ["", (f"AP75 recovery (int8_qat_qdq vs int8_minmax): {d['recovery']['AP75']}; "
                   f"QDQ met: {d['qdq_met']} (recovery {d['qdq_recovery_met']}, every-ckpt ≤ bar "
                   f"{d['qdq_every_ckpt_met']}); learned ranges verified in exported graph: "
                   f"{res['all_ranges_verified']} ({res['ranges_verified']})")]
    return "\n".join(lines) + "\n"


# ================================================================== H43d: more QAT iterations, same
# learned-range QDQ export as H43c. docs/research/66 H43d, pre-registered in 32. Unlike H43c (which
# reused H43b's 150-iteration qat.pt as-is), H43d fine-tunes fresh at cfg["qat"]["iters"] (600, same
# recipe otherwise: AdamW, H51 auto LR / 10, batch 8, imgsz 640) for each checkpoint, then applies the
# identical learned-range QDQ export (_collect_qat_ranges / _qdq_from_ranges / verify_learned_ranges_
# carried) used in H43c. fp32_torch and int8_minmax are iteration-independent and reused from H38/H43b;
# qat_fp32 and int8_qat_qdq are evaluated fresh because they depend on the new fine-tune.

def h43d_one(cfg: dict[str, Any], out: Path, name: str) -> dict[str, Any]:
    from ..baselines.run import eval_det
    from survsim.datasets.build import load_manifest
    from .detection import _eval_manifests

    h43_out = rpath(cfg["h43_out"])
    ck = cfg["checkpoints"][name]
    cp = out / "ckpts" / f"{name}.json"
    rec = json.loads(cp.read_text()) if cp.is_file() else {"arms": {}, "source": ck}
    work = out / "work" / name
    work.mkdir(parents=True, exist_ok=True)
    shape = cfg["input_shape"]
    frames = json.loads((h43_out / "calibration_frames.json").read_text())["real"]

    qpt = work / "qat.pt"
    if not qpt.is_file():
        rec["qat"] = qat_finetune(rpath(ck["pt"]), rpath(ck["data"]), qpt, cfg["qat"], cfg["seed"])
        write_json(cp, rec)

    if "verify" not in rec:
        q32 = _onnx_fp32(qpt, work / "qat_fp32.onnx", shape)
        ranges = _collect_qat_ranges(qpt, frames, shape)
        dst = work / "int8_qat_qdq.onnx"
        if not dst.is_file():
            meta = _qdq_from_ranges(q32, dst, ranges, frames, shape)
        else:
            meta = json.loads((dst.parent / "meta.json").read_text())
        write_json(dst.parent / "meta.json", meta)
        rec["verify"] = verify_learned_ranges_carried(dst, meta)
        write_json(cp, rec)

    h38 = json.loads(rpath(ck["reuse_h38"]).read_text())["arms"] if ck.get("reuse_h38") else None
    h43b = json.loads((h43_out / "ckpts" / f"{name}.json").read_text())["arms"]
    paths = {"fp32_torch": str(h43_out / "work" / name / "model.pt"),
             "qat_fp32": str(work / "qat_fp32.onnx"),
             "int8_qat_qdq": str(work / "int8_qat_qdq.onnx")}
    m = load_manifest(_eval_manifests(cfg, out)["mot20_02"])
    eval_frames = [str(Path(m["_root"]) / v) for r in m["runs"] for cc in r["cameras"].values()
                   for v in cc["frames"].values()]
    for arm in H43C_ARMS:
        if arm in rec["arms"]:
            continue
        if arm in ("fp32_torch", "int8_minmax") and h38 is not None:
            src = h38["fp32_torch"] if arm == "fp32_torch" else h38["int8_real"]
            rec["arms"][arm] = {**{k: src[k] for k in ("AP", "AP50", "AP75")}, "reused_from": "h38"}
            continue
        if arm in ("fp32_torch", "int8_minmax") and arm in h43b:
            src = h43b[arm]
            rec["arms"][arm] = {**{k: src[k] for k in ("AP", "AP50", "AP75")}, "reused_from": "h43b"}
            continue
        t0 = time.time()
        det = eval_det(m, detect_cpu(m, paths[arm], cfg["eval_imgsz"]))
        rec["arms"][arm] = {
            "AP": round(det["all"]["AP"], 4), "AP50": round(det["all"]["AP50"], 4),
            "AP75": round(det["all"]["AP75"], 4), "eval_seconds": round(time.time() - t0, 1),
            "cpu_latency_ms_median": latency_ms(paths[arm], shape, eval_frames,
                                                cfg["latency"]["n"], cfg["latency"]["warmup"]),
            "file_mib": round(Path(paths[arm]).stat().st_size / 2**20, 2)}
        print(name, arm, rec["arms"][arm], flush=True)
        write_json(cp, rec)
    return rec


def run_h43d(cfg: dict[str, Any], out: Path) -> dict[str, Any]:
    names = list(cfg["checkpoints"])
    ck = {n: h43d_one(cfg, out, n) for n in names}
    mets = {met: {a: [ck[n]["arms"][a][met] for n in names] for a in H43C_ARMS} for met in ("AP", "AP50", "AP75")}
    ranges_verified = {n: ck[n]["verify"].get("ok", False) for n in names}
    return {"checkpoints": ck, "metrics": mets, "ranges_verified": ranges_verified,
            "all_ranges_verified": all(ranges_verified.values()),
            "mean": {met: {a: round(float(np.mean(v)), 4) for a, v in d.items()} for met, d in mets.items()},
            "decision": decide_h43c(mets, cfg)}
