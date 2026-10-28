# AUDIT_H25 · Label-noise injection (32 §H25)

> **Superseded in part (2026-09-27, AUDIT_LEDGER §10):** the 'clean gain +0.0127' baseline is a 6-epoch real-only arm, i.e. unequal steps (AUDIT_H26, AUDIT_13_12 #6); do not quote it as the dose gain (R51).

Audited 2026-09-27 against `c1100bb` (32 as written). Method as AUDIT_H22_H33: every number in
32's H25 pre-registration and results recomputed in Python from
`out/experiments/h25_label_noise/results.json` (`arms[*].dataset`, `arms[*].eval`, `seed_summary`,
`analysis`, `wall_seconds_this_invocation`); method claims checked against
`survsim/experiments/label_noise.py` and `inject_label_noise` / `build_train_set` in
`survsim/experiments/detection.py`.

## 1. Recomputed

| claim in 32 | recomputed | result |
|---|---|---|
| 27 runs (4 σ × 2 drop × 3 seeds + 3 real-only) | 27 arms in `arms` | match |
| wall 6,879 s | 6,878.8 s | match |
| "no waits needed" | `gpu_wait.waited_s` = 0 in all 27 arms | match |
| real-only reproduces h14b mix_0 0.4857 / 0.4860 / 0.4860 | `analysis.real_only_AP` identical | match |
| clean gain +0.0127 [+0.0114, +0.0133] | same | match |
| table: 8 cells × {AP mean, gain + CI, − clean + CI, retained} | all 40 values equal to 4 d.p. (retained to 2 d.p.) | match |
| σ 10 % retains 97 % | 0.974 | match |
| worst cell j10_d10 94 %, −0.0008 [−0.0010, −0.0006] | 0.939, same CI | match |
| not monotone in σ (0.4981 → 0.4979 → 0.4982) | `monotone_in_sigma: false`; j02/j05/j10 d00 means as quoted | match |
| branch "refuted", testable | `branch: refuted`, `testable: true` | match |
| 447 of 11,452 boxes (3.9 %) seed 0 | 11,452 − 11,005 = 447 | match, but seed-0 only and per-step, not per-unique-box — **imprecise** → seeds 1–2 (4.2 %, 4.0 %) and unique share 447/2,648 = 16.9 % added (real ×5 repeat) |
| "the real labels dominate the loss" | true per step; overstates it for the label set | **imprecise** → qualified |
| "explains H15's null" | H15 ran at dose 300, H25 at dose 100; H25 cannot explain a result at another dose | **overclaim** → "consistent with", dose mismatch stated |
| drop = 10 % | realised 42/447, 51/480, 50/459 = 9.4–10.9 % | not stated → added |
| noise on synthetic only, paired draws | `inject_label_noise` is called only on synthetic items; RNG `[seed, 25]` draws 4 normals + 1 uniform per box regardless of σ/drop → shared directions, nested drops | match |
| sign-flip floor p = 0.25 at n = 3 | 2/2³ = 0.25 | match |

Minor, not fixed (outside 32): the results JSON's top-level `batch_dir` is `out/batch_v7` while
every arm's synthetic spec points at `out/batch_v8`; the arms are what trained.

## 2. Interpretation carried to the corpus

At dose 100 the gain is not carried by synthetic box geometry (H25), and at dose 300 amodal vs
visible geometry has no effect (H15). Together: the gain is most likely image-level/context. This
bounds how much labelling precision synthetic data needs **and** limits what perfect GT buys for
detection at this dose — stated both ways in 64 §4.2, 48 C8d, 52, 60, 65.

## 3. Score

18 claims checked: 14 match, 3 imprecise/overclaim fixed in 32 in place, 1 omission added.
**Score 15.5 / 18 (86 %)** — no number was wrong; the defects were interpretation (H15 dose) and
the box-share denominator.

Propagated: FACTS_VERIFIED (H25 row), 52 §4.4 register + status, 64 register + §4.2 paragraph,
60 #35, 48 C8d + #42, 65 N5b, 23 label-lever row, 66 (H25 done; H26 running), 00 index.
