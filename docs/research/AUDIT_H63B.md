# AUDIT_H63B — adversarial audit of H63b (corroboration mismatch on tracker-fed identities)

Scope: 32 §H63b (pre-registration + results), `survsim/experiments/uniform_disguise_tracker.py`,
`survsim/experiments/configs/h63b_uniform_tracker.yaml` (the brief's `configs/h63b_uniform_tracker.yaml` does not
exist; the repo convention path is correct), `out/experiments/h63b/results.json`,
`docs/research/figures/h63b_recall_fa.png`, FACTS row H63b. Audited 2026-09-28, mock backend, CPU.

## Reruns (scratch, not committed)
| run | gt b | osnet b | C gt → osnet | a gt → osnet | b drop | met |
|---|---|---|---|---|---|---|
| committed, 10 seeds | 0.740 | 0.700 | 0.766 → 0.709 | 0.028 → 0.249 | 0.040 | no |
| same runner, 3 seeds (seeds 0–2) | 0.743 | 0.694 | 0.770 → 0.704 | 0.036 → 0.261 | 0.049 | no |
| role re-drawn from the body **at each alarm**, 3 seeds | 0.740 | 0.734 | 0.767 → 0.761 | 0.022 → 0.027 | 0.007 | no |

The 3-seed rerun reproduces the committed result within seed noise (note b's drop 0.049 sits right at the 0.05
bar — criterion (1) is seed-sensitive). The role-at-alarm variant (a one-line change: role drawn per alarm from
`kinds[body]` instead of cached per track id at its first tick) is the key new evidence.

## Claims
| # | claim | verdict | fix |
|---|---|---|---|
| 1 | Swap hazard 0.13203 × 71.6/83.4 = 0.11335 /close-pair-s | **OK** (arithmetic; 71.6 / 83.4 = docs/13 batch_v8 day 12-seq IDSW totals, OSNet-ImageNet vs ByteTrack). Assumes IDSW ∝ hazard (linear, H59 calibration) and a ground-plane model for per-camera IDSW — already listed as a confound. | none |
| 2 | "Registered … before the full run" | **UNEVIDENCED** — `git log -S` shows the pre-registration first appears in be425c0, the same commit as results, figure and FACTS row. H63 had a separate pre-reg commit (d411fb2); H63b did not. | annotated in 32 |
| 3 | Bootstrap "over clips (world), all seeds kept" | **OK** — per-world sums over seeds, worlds resampled, same indices for gt and osnet (paired). p = 0.0005 is the 1/(2000+1) floor, so Holm 0.0015 is a floor too (report as ≤). | none |
| 4 | Holm over {b, s, g} | **OK** as registered; the three drops are near-identical and highly correlated, so the family is conservative, not anti-conservative. | none |
| 5 | Naive (a) rises 0.028 → 0.249 because swaps land intruders on commuter-born tracks — "works by accident" | **ARTEFACT** of caching role at track birth: with the role re-drawn per alarm, (a) stays 0.027. It says nothing about a tracker that classifies appearance per detection. | 32 + FACTS qualified; **R64** |
| 6 | b's 0.040 drop is "almost all the base detector's, not the rule's: C itself drops 0.766 → 0.709 because breaks and swaps split the crossing" | **WRONG** — C is not role-free (its non-guard alarms go through the H53 badge/RF drop, so an intruder on a commuter-born track near a tagged guard is dropped). With per-alarm role C holds 0.761 and b drops only 0.007. The drop is mostly the role cache. | 32 + FACTS corrected; **R64** |
| 7 | (3) "sticky drops more than live … by 0.001 (31 hits)" | **FIX** — drop gap is 0.0007 (≈ 2 hits); 31 is the osnet-arm level gap b − s. Noise. | 32 corrected |
| 8 | (4) grace recovers over sticky; "live beats both"; robust to window? | **TRUE BY CONSTRUCTION** — `guard_keep` keep sets are nested (s ⊆ g ⊆ b) for every grace window, so recall and FA are ordered live ≥ grace ≥ sticky at any window length. Criterion (4) could not fail except by equality; the only measured content is the FA trade (0.020 vs 0.018 gt; 0.016 vs 0.015 osnet). "Don't carry history" is a value judgement on that trade, and it holds for any window. | 32 annotated; regression test `test_keep_sets_nested_for_any_grace` |
| 9 | Body-keyed vs 2 m position-keyed "agree within 0.006" | **FIX** — C: 0.709 vs 0.716 (0.007); b/s/g 0.005. | 32 corrected |
| 10 | gt arm 0.740 reproduces H63's 0.745 | **OK** (10 noise seeds vs 1). | none |
| 11 | Twin FA b 0.020 → 0.016, ≤ 0.05 | **OK**, matches results.json (604 / 492 FAs). | none |
| 12 | Figure `h63b_recall_fa.png` | **OK** — bars/CIs drawn from results.json; label says simulated sensors, 10 seeds. | none |
| 13 | FACTS row | **OVERSTATED** on items 5–6 (now qualified); other numbers match results.json. | FACTS edited |

## Bottom line
Decision "not met" stands and reproduces. The substantive conclusion changes: the H63 rule is robust to
ID switches **if** the role is classified per alarm; the modest loss measured by H63b comes from caching
the appearance role per track id, which is a design choice to avoid, not a detector limit.
