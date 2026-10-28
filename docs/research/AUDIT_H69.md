# AUDIT_H69 · adversarial audit of H69 (cross-site generalisation), 2026-09-28

Sources: 32 §H69 (pre-registration 7f3d2ce 02:47 → interim 0727b9c 02:54 → results 6df8784 03:17; order confirmed),
`survsim/experiments/site_generalisation.py`, `survsim/experiments/configs/h69_site_generalisation.yaml`,
`out/experiments/h69/{results.json,detections}`. Everything recomputed from the cached detections on the same
16 sites (no GPU, no editor). Frames inspected: 05 frames 25–26, 09 frames 5/20, 17 frames 5/20 (GT boxes drawn).

| # | Claim | Verdict | Evidence | Fix |
|---|---|---|---|---|
| 1 | H69b "met, not vacuous" at B = 3600 FA/cam-h | **Holds; budget is a detector-FP rate, not an alarm budget** | The docs/13 operating point (conf 0.25) itself runs at 6150 /cam-h pooled (0.171 FP/frame), so 3600 is tighter than docs/13, not near-vacuous. Within-budget fraction of 200 splits: 0.535 at B = 6150 (θ median 0.25), 0.50 at 3600, 0.415 at 1200; θ never at grid minimum. Below ≈ 1200 the budget is unresolvable (one FP in a 30-frame site = 1200 /cam-h; B = 360 and 36 give the same 0.51). Rerun at 3600 gives 0.50 vs committed 0.53: RNG-state sensitivity only | 32 audit section; FACTS row qualifier |
| 2 | Within-site CIs / hard negative | **Holds, CIs were too narrow** | 5-frame block bootstrap (6 blocks/site): corrected SD 0.354 [0.209, 0.433] (committed 0.355 [0.197, 0.431]); hard negative still FAILS, 12/16 pairs differ (committed 13/16; 03 vs 15 now covers 0). 12's CI stays degenerate | FACTS, 32 |
| 3 | ≤ 0.10 sites are "real detector failure … with visible, usable targets present" | **Retired (R68)** | 05: only 8 GT rows in the rendered window, frames 25–29, 3.5–6 px-wide slivers at the right image edge (x ≈ 634–640). 09 (dusk) and 17 (night): 21–29 px tall, 7–10 px wide people standing behind fence railings; GT vis 0.8–1.0 because the visibility label does not model thin railings; in the crops they are barely discernible. Lighting contributes (dusk/night) but the dominant cause is occlusion the GT misses | 32 qualification 3 corrected; R68 |
| 5 | licences.json commercial_ml_ok | **Holds** | `true` on all 23 generated sites, incl. the 16 used | — |
| 6 | Camera height 4.5 m everywhere | **Design, not a bug** — hard-coded `pos = [..., 4.5]` and pitch from `4.5 - 0.9` in `tools/infinite_sites.py` (read only, not touched). H69c's height term is a constant; the registration should have caught it | noted in 32 / FACTS |
| 7 | Reproducibility of N = 16 | **Qualified** | Site 21 passed its gate at 03:18, after results.json (03:15). An unpinned re-scan now gives N = 17: H69b 0.415 at 3600, hard negative 14/19. The committed numbers are for the 16 sites listed in results.json | 32 audit section |
| 8 | FACTS / 32 sentences; H70 σ_δ from H69 | **Consistent** | FACTS row matches results.json. H70's σ_δ = 0.3 was matched to the *interim* 56.5 %; final 0.53 (rerun 0.50) is in the same direction; unit mismatch already noted in AUDIT_H70 (H70 files not touched) | — |

0.97 recall under the docs/13 all-rows denominator, but the lowest sites are GT artefacts (edge slivers, people
behind railings the visibility label misses); what survives is that a pooled FP threshold transfers to held-out
sites only about half the time, so calibrate per site.

**Follow-ups (not done):** model thin occluders (railings) in GT visibility; pin the site list in the config;
more frames per site so a sub-1200 /cam-h budget is resolvable.
