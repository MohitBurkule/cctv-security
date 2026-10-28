# AUDIT_H3D — adversarial audit of H3d (tile-merge strategies)

Scope: 32 §H3d (pre-registration 3d056ec, results 6c8a233), `survsim/experiments/tile_merge.py`,
`survsim/experiments/configs/h3d_tile_merge.yaml`, `tests/test_tile_merge.py`,
`out/experiments/h3d/results.json`, FACTS row, 65 v2 item 21 and 103 §2 tiling sentences.
All recomputation is CPU-only, from the cached detections in `out/experiments/h3d/dets`
(scratch script re-uses the runner's `items_of`, `merge`, `frame_counts`, `make_blocks`; 30-frame
blocks, 1000 resamples, seed 0). The reported table reproduces exactly (far 0.682 [0.521, 0.829] for (d)).

## Verdicts

| # | Question | Verdict |
|---|---|---|
| 1 | Runner / config / test unchanged between 3d056ec and 6c8a233? | **Yes.** `git diff 3d056ec 6c8a233` touches none of the three files. |
| 2 | FP cap re-based from "≤ 72" to 292 after registration? | **No.** The registered text (3d056ec) already reads "near FP ≤ 2× full_1280's near FP on the same cache … the cap is taken from this run's full_1280, not a fixed 72", and the frozen config has `near_fp_factor: 2.0`. 72 appears only as the rejected alternative. Decision is **met under the registered cap**, not a re-based one. |
| 3 | How does (d) get near AP50 0.973 > full_1280 0.944? | **Not an artifact of dropping boxes.** full_640 alone already scores 0.954 > full_1280 — full_1280 misses large near people (≥ 80 px recall at 0.25: 0.910 vs 0.951 full_640, 0.972 (d)). (d) keeps full_640's large-person recall and adds tile recall on small near people (20–40 px: 0.692 full_640 → 0.833 (d); 1280 0.846), while the border rule removes the fragments that cost (a) its precision. So yes: the **same small-person tile gain that fails (e)'s hard negative** is inside (d)'s AP50 — (d) raises near 20–40 px recall as much as (e) does. That gain is desirable; (e)'s HN failed only because it contradicts (e)'s "far cameras only" premise. Label: near AP50 gain = large-person recall of the 640 pass + tile recall on small near people, not FP removal alone. |
| 4 | Is (b)'s IoM 0.6 tuned on the test data? | **No evidence of tuning** (registered before any detection was cached), and it is insensitive: IoM 0.5 / 0.6 / 0.7 → near FP 156 / 159 / 162, far 0.676. (d) is also insensitive: border IoM 0.3 / 0.5 / 0.7 → 123 / 133 / 156; margin 1 / 3 / 6 px → 133 at all three. |
| 5 | Bootstrap CIs (conf 0.25, pooled) | Near FP [95 % block CI]: full_1280 146 [85, 212]; (a) 979 [691, 1247]; (b) 159 [106, 219]; (d) 133 [86, 188]; (e) 914 [650, 1168]. Paired (FP − 2 × full_1280 FP): (b) −133 [−232, −32], (d) −159 [−267, −57] — both clear the cap with CI excluding 0. Far ≥ 20 px: (b) 0.676 [0.517, 0.824], (d) 0.682 [0.521, 0.829]; **the far lower bounds are well below 0.65** — the far bar is met on the point, as registered, not with confidence. |
| 6 | Robust to conf 0.4? | **Partly.** Near FP at 0.4: full_1280 37, (b) 82 (> cap 74 — **(b) fails**), (d) 42 (passes; FP − cap −32 [−85, +14]). But far ≥ 20 px recall at 0.4 is 0.592 [0.409, 0.766] for every tile arm, **below 0.65 — no strategy meets the decision at conf 0.4.** The pass is a conf-0.25 result. (d) is the robust choice between the two. |
| 7 | Degraded stream | Near FPs: the border rule holds (day degraded (d) 54 vs full_1280 69; FP − cap −84 [−130, −40]). **Far recall does not:** day-degraded far ≥ 20 px is 0.295 [0.180, 0.372] for every tile arm (full_1280 0.055) vs day raw 0.894, night raw 0.857. The pooled 0.682 is carried by the raw streams; on the degraded stream the far bar is not met by any arm. |
| 8 | FACTS / 32 sentences honest? | Numbers correct. Three omissions fixed by an appended audit note in 32 §H3d and a FACTS row: (i) pass is conf-0.25 only, (ii) far bar met on the point with lower CI bound ~0.52, not on degraded, (iii) AP50 "rise" source. "(d) removes every tiling FP" is fair (133 < 146) — keep. |
| 9 | H3c "about eight-fold near FPs" in 65 v2 item 21 / 103 §2 stale? | **Qualified, not retired.** The eight-fold figure is true for plain NMS (H3d (a) 979 vs 146, 6.7× here; 8× in AUDIT_H3C's subset). One-line qualifier added: fixable by the tile-border merge rule (H3d, 133 vs 146), and degraded-stream far recall is only ~30 %. |

## Nothing retired
No quoted H3d number is wrong; no RETIRED_CLAIMS row. The decision stands as **met (registered cap 292) by (b) and (d) at conf 0.25, on the pooled point estimate**; recommended (d) survives every sensitivity check except the far bar at conf 0.4 and on the degraded stream, which no strategy meets.

## Honest far-field sentence
"On customer-safe CC0 renders, 320×240 tiles at 2× lift far ≥ 20 px recall from 49 % (1280 input) to 68 % at conf 0.25 (block CI lower bound 52 %) at 6–7× detector cost; the tile-border merge rule removes the near-camera false positives plain NMS adds (133 vs 146 at 1280, vs 979 with NMS). It is a conf-0.25, raw-stream result: at conf 0.4 far recall is 59 %, and on the degraded stream 30 %."
