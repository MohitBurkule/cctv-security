# AUDIT_H19_H20 · Far-field v3 and synthetic ReID (32 §H19, §H20)

Audited 2026-09-27 against `cfa9c2a` (32 as written). Method as AUDIT_65: every number in 32's
H19/H20 pre-registration and results sections recomputed in Python (`.venv`) from
`out/experiments/h19_farreal_v3/results.json` and `out/experiments/h20_reid_train/results.json`
(arm means over seeds, contrasts, per-arm `dataset` / `train_cost`, `scores`, `contrasts`); method
claims checked against `survsim/experiments/reid_train.py` (identity keys l.27–47, protocols l.70–80,
`summarise` l.195–209: query-weighted point, bootstrap over **identity means**) and
`survsim/experiments/farreal.py` + `configs/h19_farreal_v3.yaml` (arm recipes).

## 1. H19 — recomputed

| claim in 32 | recomputed | result |
|---|---|---|
| mean-AP50 table, 6 arms × 7 methods | all 42 cells equal to 3 d.p. | match |
| P1 v8_syn − v6_syn 0.000 [0, 0] | diffs [0, 0, 0], p 1.0 | match (floor) |
| P2 +0.817 [+0.812, +0.824], all 3 + | 0.8174 [0.8122, 0.8243]; p 0.25 | match; p floor unstated → added |
| mix1280 − real_only +0.035 [+0.026, +0.040]; native −0.061 [−0.079, −0.046] | 0.0349 [0.026, 0.0399]; −0.0611 [−0.0793, −0.0459] | match |
| mix1280 − mix640 +0.036 [+0.031, +0.040]; native −0.079 [−0.104, −0.056] | 0.0363; −0.0789 [−0.1044, −0.0564] | match |
| v8_syn 796 imgs (396 raw + 400 degraded), v6 596 | `dataset.train_images` 796 / 596 | match |
| "372 s/seed" | v8_syn 371.5 / 251.5 / 290.4 s | **imprecise** — seed 0 only |
| "fixes change nothing (≤ 0.014 under any method)" | seed-means ≤ 0.014 true; at native P1 +0.0044 [+0.0032, +0.0050], 3/3 + | **imprecise** — negligible, not nothing |
| "collapse" in all 3 seeds | both syn arms 0.000 < 0.5 × 0.613; recall@0.25 = 0.000 every seed | match (stronger than stated → added) |
| registered branch "the real mix removed it" | v6 collapses, v8 collapses, mix does not | match |

## 2. H20 — recomputed

| claim in 32 | recomputed | result |
|---|---|---|
| "23 distinct identities" (13 + 3 + 5 + 7) | the listed parts sum to **28**; results.json has 16 train candidates, 15 used, 13 held-out keys | **false arithmetic** — annotated in place |
| 15 train ids, 4,204 crops; passer_by_11 dropped | `train.n_ids` 15, ids list lacks passer_by_11 | match |
| "13 held-out synthetic ids" | 13 keys, but cross-camera scores **9** ids (336 q), cross-time 12 (333 q) | **imprecise** — fixed |
| 105 MOT20 ids, 51 valid, 167 queries | `mot20.n_ids` 105; scores n_ids 51 / 167 | match |
| sanity 0.180 / 0.228 | 0.1796 / 0.2275 | match |
| table: HSV 0.273 [0.175, 0.456] etc. | point = query-weighted (0.2733), CI = id-mean bootstrap (id-mean 0.2998) | **imprecise** — two statistics in one cell; convention note added |
| Δ synth cross-camera +0.324 [+0.197, +0.493]; per seed +0.276/+0.315/+0.382 | 0.3244 [0.1965, 0.4932]; 0.2758/0.3152/0.3821 | match (id-mean) |
| Δ cross-time +0.204 [+0.139, +0.261] | 0.2037 [0.1391, 0.2608] | match |
| Δ MOT20 +0.021 [−0.047, +0.097]; per seed +0.017/+0.034/+0.013 | 0.0213 [−0.0471, 0.0967]; 0.0165/0.0342/0.0133 | match; each per-seed CI spans 0 → added |
| "0.21 → 0.50" | query-weighted 0.208 → 0.496 (id-mean 0.194 → 0.518) | match, but Δ +0.324 is id-mean → labelled |
| "barely moves real pixels (0.228 → 0.249)" | query-weighted FT mean **0.243**; id-mean 0.239 → 0.261 | **false** — 0.249 matches neither; fixed |
| 242–270 s/seed | 242.0 / 269.6 / 270.1 | match |
| "1.34 GB peak" | 1,346 MiB (= 1.41 GB) | **imprecise units** — fixed to MiB |
| held-out = unseen people | keys are scene:uid:epoch; `loiterer_200` exists in train (street_crowd) and test | **caveat added**: held out by scene, not provably by appearance |
| UnrealPerson 19.3 % MSMT17, ~3,000 ids | FACTS l.140/144 (2012.04268, 2204.02611) | match; "direction not magnitude" framing kept |

## 3. Fixes applied in place (32)

1. H19 train time → 252–372 s (mean 304), other arms' ranges; synthetic-only recall 0.000 stated.
2. P2 row: sign-flip p 0.25 (n = 3 floor).
3. "change nothing" → "nothing measurable"; native +0.004 stated.
4. H20 "23 identities" annotated (28 by its own parts; not recoverable); held-out-by-scene caveat.
5. Held-out ids: 9 cross-camera / 12 cross-time.
6. Table convention note (query-weighted points, id-mean CIs and Δs).
7. 0.228 → 0.249 corrected to 0.243 (query-weighted) / 0.239 → 0.261 (id-mean); per-seed CIs span 0.
8. 1.34 GB → 1,346 MiB.

Downstream: FACTS rows added (H19, H20; H18 row "cause unresolved" → resolved); 52 §4.4, 64 §4 register
and §4.1 + ReID paragraph, 60 items 29–30, 48 numbers 38–39 + Q&A C9b/C9c, 65 N11 + retired list, 66 H27 (retired
by its own stopping rule) / H29 (motivation), 23 far-field / ReID / M15 rows.

## 4. Score

| criterion | before | after |
|---|---|---|
| H19 numeric accuracy vs results.json | 9.5/10 | 10/10 |
| H20 numeric accuracy vs results.json | 7/10 (0.249, 1.34 GB) | 10/10 |
| statistic labelling (query- vs id-weighted) | 5/10 | 9.5/10 |
| identity accounting (23, 13 vs 9) | 4/10 | 9/10 (23 unrecoverable, flagged) |
| claim truth vs registered decision rules | 10/10 | 10/10 |
| caveats (p floor, per-seed CIs, name overlap) | 7/10 | 10/10 |
| provenance | 10/10 | 10/10 |
| **total (×100/70)** | **75/100** | **98/100** |
