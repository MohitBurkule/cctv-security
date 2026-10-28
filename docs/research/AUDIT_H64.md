# AUDIT_H64 — adversarial audit of H64 (PTZ-tour timing exploitation)

Scope: 32 §H64 pre-registration (e52f977, 02:38) and results (f853a1d, 02:41), `survsim/experiments/patrol_timing.py`,
`survsim/experiments/configs/h64_patrol_timing.yaml`, `out/experiments/h64_patrol_timing/{results,sensitivity}.json`,
`docs/research/figures/h64_patrol_timing.png`, FACTS H64 row. Order confirmed by `git log`: the pre-registration
commit touches only 32; code, config and numbers first appear in f853a1d.

Rerun (reduced): 500 worlds × seeds {64, 65, 66}, 500 calibration worlds each. tau 618 / 587 / 611 s; naive catch
fixed 0.164 / 0.192 / 0.166, random 0.160 / 0.162 / 0.186; timed catch 0.000 at every N, both tours, all seeds;
fixed recon N ≤ 3 0.000, N = 5 0.294 / 0.454 / 0.328; random recon N = 3 0.054 / 0.096 / 0.074; innocent FA
0.482 / 0.574 / 0.478 /cam-h; decision T1 pass, T2 fail, T3 fail, FA pass — NOT met on every seed.

| # | claim | verdict | fix |
|---|---|---|---|
| 1 | Timed intruder caught 0.000 under both tours | TRUE BY CONSTRUCTION. Return ≥ leave + 2 + d + 2; crossing [leave + 1, leave + 1 + c], c ≤ 15; overlap ≥ 2 s needs d ≤ c − 5 ≤ 10, and d ~ U(10, 30) → measure zero. Fixed tour: gap 112 s. Labelled in 32 qual. 1 and FACTS ("by construction") | none needed; 32 interview sentence now says so too |
| 2 | "a ~16 % duty-cycle sensor" (interview sentence, 32 qual. 1 "coverage duty cycle ~0.16") | WRONG LABEL. 0.162 is an identity p_det × (dwell + E[c] − 2·overlap)/period = 0.775 × 27.5/132 = 0.161, not measured; duty cycle is 20/132 = 0.152 | 32 text corrected; FACTS row annotated; retired as R66 |
| 3 | Recon rule uses H33-style calibration | NO. Plug-in empirical quantile (smallest dwell with ≤ 0.5 FA/cam-h) on a declared LogNormal(240 s, 0.6) — not H33 conformal/CRC, not the engine's `commute_wait`. Test FA 0.459 meets budget; tau moves 587–618 s with 500 calibration worlds | stated in 32 addendum |
| 4 | Recon flagged 0.000 at N = 3 | FIXED TOUR: BY CONSTRUCTION — recon dwell ≤ 3 × 132 + 16 = 412 s < tau. Random tour is not zero (0.05–0.10), still < 0.5. FACTS quoted only the fixed zero, unlabelled | FACTS annotated |
| 5 | Naive intruder a fair baseline | FAIR. t_a ~ U(600, 2400) plus U(0, 60) delay against a U(0, 132) tour phase → crossing phase uniform; analytic 0.161 matches 0.162 | none |
| 6 | E_random ≈ E_fixed; randomising does not halve exploitation | DEPENDS ON DWELL LAW. Any random dwell floor > 10 s gives timed catch 0 exactly; U(2, 38) gives 0.020 (post-hoc, labelled). The conclusion survives for any floor ≥ ~2 s, but its size is geometry | none; sensitivity already labelled post-hoc |
| 7 | T3 failure sensitive to N | NOT SENSITIVE in the decision direction: fails at N = 1, 2, 3 (both tours) and N = 5 (0.29–0.45 < 0.5, capped by p_vis 0.7) | none |
| 8 | Hard negative is real | DECLARED, NOT MEASURED. Commuter wait is a synthetic LogNormal, always visible; attacker visible 0.7. "Shorter than a bus-stop wait" is true of the declared law only | 32 interview sentence qualified |
| 9 | Holm p 0.0015 for T1 | bootstrap floor (1/2001 × 3); T1 is also by construction (E_fixed = naive catch) | none (labelled in 32) |

Honest interview sentence: *In a simulated one-dome fence, a naive crosser is caught about 16 % of the time — that is
p_det times the overlap window, arithmetic not measurement — and an intruder who goes the moment the dome turns away
is caught 0 % under a fixed or a randomised tour, by construction of the tour geometry. The test that could have gone
either way was the recon: under a declared commuter-wait law, a dwell rule at 0.5 false alarms per camera-hour never
flags a one- to three-pass watcher. Fixed overlap or a fence sensor, not a cleverer tour.*
