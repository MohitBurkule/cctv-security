# AUDIT_H3C · Adversarial audit of H3c (H3's exact tiling arm on CC0 batch_v8)

Scope: 32 §H3c (pre-registration fe6e5e5 with runner + config, results 7b8a977),
`survsim/experiments/far_field_h3c.py`, `survsim/experiments/configs/h3c_tiling_arms.yaml`,
`out/experiments/h3c/{results,partial}.json`, figure `h3c_tiling_arms.png`, FACTS row; compared with
AUDIT_H3B. Re-run 2026-09-28: 198 frames (22 per stream, `max_frames_per_stream: 22`, 500 resamples,
same code path via `far_field_cc0.run`), GPU 2.8 GB in use (Unreal editor, 84 % utilisation), no
`/tmp/survsim_jobs/*.running`. There is no detection cache, so the re-run re-detected.

## Verdicts

| # | Question | Verdict |
|---|---|---|
| 1 | Frozen runner = what ran? | **Confirmed.** `git diff fe6e5e5 7b8a977` is empty for `far_field_h3c.py`, the config and the shared loop `far_field_cc0.py`. The AUDIT_H3B gap (code committed with results) is closed. |
| 2 | 30-frame blocks over 891 frames | Far: 6 streams × 99 sampled frames → **24 blocks** (18 × 30, 6 × 9); near: 12. The day-degraded stream repeats the day-raw moments, so ≈ 16 independent far blocks — the CI is optimistic. The decision lower bound (+0.119) is far from 0; on the 198-frame re-run (6 far blocks) Δ is +0.155 [+0.048, +0.289], still > 0. **Decision robust; CI widths indicative.** |
| 3 | NMS across tile borders — double counting? | Recall is one-to-one matched, so duplicates cannot add hits. **Far:** precision at conf 0.25 full_1280 / 2.0× / 1.5× = 0.769 / 0.815 / 0.723 (489/636, 767/941, 723/1000) and far AP50 rises (0.540 → 0.779 re-run; 0.497 → 0.741 main): the far gain is real, not FP inflation. **Near: not clean.** FP 36 → 300 for 2.0× (precision 0.931 → 0.625), 192 for 1.5×. Tiles cut near people into fragments whose IoU with the full box is < 0.5, so NMS 0.5 keeps both. 32's "tiling is not a far-field-only effect" read a near recall gain (+0.038) as a benefit; it is bought with 8× the false positives. Text fixed. |
| 4 | ≥ 20 px primary alongside all rows | **Honest.** 32, FACTS and row.md give both (0.681 / 0.643 for the 2.0× arm) and n (1758 of 5061). |
| 5 | "~7× latency" | GPU memory 2.8 GB < 4.5 GB but the GPU was 84 % busy with the Unreal editor, so an **idle** timing is **untestable** now. Second (busy) timing: 18.1 / 114.1 / 59.3 ms → 2.0× arm 6.3× (main run 7.4×). The 1.5× arm moved 114.4 → 59.3, so single timings are unstable. Say **"6–7×, shared GPU"**. |
| 6 | Near AP50 drop 0.043 vs 0.05 bar — tuned pass? | Not tuned: the bar and arms are in the frozen config. But **marginal**: passes by 0.007 on the full set and **fails on the subset** (0.941 → 0.854, drop 0.087). The hard negative does not gate `decision_met` (as registered), so the decision stands; the HN should be quoted as "passes narrowly on the full set, not robust". |
| 7 | Customer-safe scope | **Correct.** 32 and FACTS call only the CC0 H3c numbers customer-safe; the H3 MetaHuman 0.629 is said to stay engineering-only (32 §H3c, FACTS H3c row). FACTS' older H3 row (0.629 "at 7× latency") carries no MetaHuman tag itself but cites 32 §H3, whose section is MetaHuman — flagged, not edited (not an H3c hunk). |
| 8 | Demo INDEX / segment 09 | Not stale in numbers: the title quotes H3c 0.491 vs 0.681, +0.190 [0.119, 0.265] and 143.3 vs 19.3 ms labelled shared-GPU. It omits the near-camera FP cost; `docs/research/demo/*` is out of scope for this audit — flagged for the demo owner. |


"On customer-safe CC0 renders, H3's small-tile arm finds 68 % of far people at least 20 px tall
versus 49 % for a 1280 input, a pre-registered +0.19 gain whose interval excludes zero, and it holds
on a re-run with far precision no worse; but it costs 6–7× the compute on our shared GPU, and on
the near camera it multiplies false positives about eight-fold, so it is a far-camera setting, not a
default."

Retired: none (the "not a far-field-only effect" line is corrected in place). Ledger: Z15.
Still unverified: idle-GPU latency; whether a larger tile-merge (e.g. box fusion) removes the near FPs.
