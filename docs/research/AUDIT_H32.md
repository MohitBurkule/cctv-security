# AUDIT_H32 · Night profiles H32a/H32b (32 §H32a/H32b results)

Audited 2026-09-27 against `1acb9bd`. Method as AUDIT_H22_H33: every number in 32's
H32a/H32b results section recomputed in Python from
`out/experiments/h32_night_profiles/results.json` (`A.real`, `A.synthetic[*].{vis,ir}_{tune,hold}`,
`A.verdict`, `B.device`, `B.frames_per_arm`, `B.models[*].per_camera`, `B.models[*].pooled`);
method claims checked against `survsim/experiments/night_profiles.py` (`split_real`, `in_band`,
`degrade_cam`, `cluster_boot`, `recall`), the config, and `survsim/sensors/degrade.py` (`thermal`,
profiles `cctv_night_lowlight`, `cctv_thermal`). 32's H34 section was not touched.

## 1. H32a (realism) — recomputed

| claim in 32 | recomputed | result |
|---|---|---|
| band table, 4 profiles × {vis, IR} × {tune, hold-out} | all 16 counts equal `A.synthetic[*].count` | match |
| lowlight 9/13 tune → 2/13 hold-out; thermal 10/13 → 3/13 | 9 → 2; 10 → 3 | match |
| both flagged overfit (tune − hold-out > 2) | `verdict.overfit_flag` true for both; `cctv_night_ir` false (3 → 2) | match |
| H32a not met (targets 9 vis, 8 IR) | `met: false` for both | match |
| vis luma band 28–39 hold-out vs 26–60 tune | p10–p90 27.8–39.4 vs 26.0–60.2 | match (rounded) |
| tune = first 15, hold-out = last 10, sorted by filename | `split_real`: `sorted(paths)[:15]`, rest | match |
| band = p10–p90, synthetic scored by median of 30 frames | `in_band` on median; config `n: 30` | match |
| "random search, ≈20–35 draws each" | no search script or draw log committed; only final params in `degrade.py` | **unverifiable** — labelled unrecorded |
| "stat bands can be gamed" (lowlight chroma noise) | 9/13 on tune with visibly wrong chroma noise (fig_h32) | match; see §3 risk 1 |

## 2. H32b (recall) — recomputed

| claim in 32 | recomputed | result |
|---|---|---|
| 8 rows recall + CI, Δ + CI (both models) | all 24 values equal `pooled` to 3 d.p. (e.g. v8 raw 573/611 = 0.9378; lowlight 63/611 = 0.1031) | match |
| "180 frames" | `frames_per_arm` 180 | match |
| "all 12 batch_v8 night cameras" (pre-reg) | 12 cameras listed, **9** with any h ≥ 40 GT (`n_cameras` 9, 611 boxes); `cam_yard`, far `cam_02`, far `cam_03` contribute 0 | **imprecise** — fixed |
| "on CPU, because the GPU was held by X8" | `B.device` `"0"`, `gpu.free_mib` 4,531 | **wrong** — fixed (GPU; cached dets may predate) |
| CI = camera-cluster bootstrap, paired Δ | `cluster_boot`: resample cameras with replacement, 10,000 draws, percentile 2.5/97.5, Δ on the same draw | match |
| P1 refuted (lowlight Δ larger than NIR Δ) | −0.835 vs −0.565; CIs [−0.888, −0.758] and [−0.660, −0.496] disjoint; YOLO26n same order | match |
| P2 holds (thermal Δ < 0, CI excludes 0) | −0.470 [−0.548, −0.394]; YOLO26n −0.383 [−0.536, −0.244] | match |
| penalty range "−0.47 to −0.84" | YOLOv8n only; YOLO26n −0.38 to −0.89 | **incomplete** — fixed |
| NIR on v8 −0.565 vs H11 −0.609 on v7, "consistent" | −0.609 inside [−0.660, −0.496] | match |
| branch B3 | no profile `met` | match |

## 3. Risks the write-up under-stated

1. **Band-count gaming.** In-band is a per-stat median inside p10–p90; a fit
   can buy a stat by overshooting another one that is not counted
   (per-channel chroma noise). With 10-frame bands the target is narrow and
   scene-specific. The count is a screen, not a realism proof (H13 already
   found the in-band count does not predict AP, ρ = +0.10).
2. **CI method.** Percentile bootstrap over **9** clusters under-covers (few
   clusters; the three street_crowd_night cameras carry 345 of 611 boxes).
   Intervals are indicative; the P1 disjointness is large enough to survive that.
3. **Seed count.** One degrade seed (0), one detector pass. The backlog asked
   for 3 degrade seeds; none of the CIs include degrade noise.
4. **Thermal leak.** `cctv_thermal` makes people hot from the render mask,
   which is also the GT source; the detector sees GT-shaped blobs. Thermal
   recall is an upper bound for this sensor model — added to 32.
5. **Tune-set reuse.** The same 30 synthetic frames (street_crowd_night cam_02)
   were used to tune and to score; only the *real* side was held out.

## 4. Score

28 checks: 23 match, 1 wrong (device), 3 imprecise/incomplete (camera count,
penalty range, unrecorded draws), 1 unstated leak (thermal mask). All fixed in
place in 32 with "*(Corrected in place, AUDIT_H32.)*" markers; the pre-registration
text is left as registered. **Score 8/10** — the verdicts (H32a not met, B3,
P1 refuted, P2 holds) all stand; the errors are in the method narrative, and the
thermal leak affects interpretation, not the verdict.
