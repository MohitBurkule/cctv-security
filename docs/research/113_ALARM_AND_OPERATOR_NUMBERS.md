# 113 · Alarm, operator, fusion and rule numbers: one reconciliation table

*2026-09-28. Mirror of `112` for the operator/alarm side: every alarm-budget, threshold, operator, fusion and
rule number quoted in `32` §H22, §H33/H33b/H33c, §H40/H40b, §H42, §H45/H45b/H45c, §H53/H54/H59/H62, §H56,
§H63/H63b, §H66, §H70/H70b, `FACTS_VERIFIED.md` and AUDIT_H22_H33 / H33B / H40B / H42 / H45 / H53 / H54 / H59 /
H63B / H66 / H70 / H70B / TAILGATER_RECONCILIATION, in one table. Numbers differ because the arm, unit, identity
source or operator model differ — not because any is wrong. Where this file disagrees with FACTS, FACTS wins.
**Everything here is simulated**: mock worlds (H12 loiter worlds, H40b fenced line-cross worlds, H70's declared
estate), never a real site.*

**Legend.** unit: FA/cam-h = false alarms per camera-hour; recall = model (actor-aware, 30 s for loiter, @10 s for
line-cross) recall; realised = realised recall after the operator queue at the stated delay (@5 min = @300 s);
θ = score threshold; util = operator utilisation. Identities: **GT** = simulator uids (perfect ReID);
**tracker** = H24-calibrated ID switches / breaks (H59, H63b); **position** = position/time keyed, `position_radius_m`
(H62, diagnostic only). Operator: **H22** = invented model (gamma 30 s review, cv 0.3, fatigue after 2 h, bulk-ack
when queue > 10), 1 operator / 40 cams unless K stated; **K-wall** = H70's K-operator FIFO wall, H22 values, fatigue
omitted; **–** = no operator (model output). Simulated: what is simulated beyond the worlds (sensors, operator,
noise, PTZ timings, estate). Status: FACTS = in FACTS_VERIFIED as-is; qualified = in FACTS but must carry the
qualifier named; R-id = retired phrasing around it; by construction = true by design, not a finding.
Budget ratios divide by *our assumed* 0.001 FA/cam-h (28 §6, R56), never a field standard.

## 1 · The table

| # | number | CI (95 %) | exp | arm | unit | identities | operator | simulated | status | allowed sentence |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.511 | [0.484, 0.537] | H22 | A1 θ 0.95, FIFO | realised @5 min | GT | H22 | operator | FACTS; R25/R26 phrasing | "one invented operator on 40 cams realises 0.511 at 5 min against a 0.495 bar — inconclusive" |
| 2 | 0.127 | – | H22 | A1 FIFO | realised @30 s | GT | H22 | operator | FACTS | only with "@30 s" |
| 3 | +0.262 / +0.075 | [+0.240, +0.286] / – | H22 | ranked − FIFO | realised @30 s / @5 min | GT | H22 | operator | FACTS | "ranking helps most at 30 s, 10/10 seeds" |
| 4 | 120 alarms/h, util 0.88, 25 % bulk-acked | – | H22 | A1 | alarms/h | GT | H22 | operator | FACTS | "120 alarms an hour keeps the operator 88 % busy" |
| 5 | 1.008 FA/cam-h, 44/h, 0.2 % bulk-acked | – | H22 | twin floor | FA/cam-h | GT | H22 | operator | FACTS; R26 | "twin floor 1.008 — track-only rules cannot go below it" |
| 6 | 0.108 | – | H22 | dwell_25 (6.007 FA/cam-h, 244/h) | realised @5 min | GT | H22 | operator | FACTS | "a looser rule floods the queue: 0.108" |
| 7 | 2.915 / 0.825 | [2.854, 2.977] FA | H23/H42 | A1 θ 0.95 | FA/cam-h / recall | GT | – | – | FACTS; R48 | "one of three H42 points" — never "A1 ships" |
| 8 | 5.033 / 0.894, range 0 | – | H42 | pooled θ 0.9 ×10 | FA/cam-h / recall | GT | – | – | qualified (range 0 partly by construction, AUDIT_H42) | "pooled is H42's selection policy; its zero spread is partly because LOFO pools share 8/9 folds" |
| 9 | FA range 2.118 (2.915–5.033), SD 1.023 | – | H42 | per-fold θ | FA/cam-h | GT | – | – | FACTS | "per-fold θ swings FA 2.915–5.033" |
| 10 | ΔFA +2.118 / Δrecall +0.069 | [+2.005, +2.237] / [+0.045, +0.095] | H42 | pooled − A1 | FA/cam-h / recall | GT | – | – | FACTS | "pooled buys 7 points of recall for 2 FA/cam-h" |
| 11 | θ 0.963–0.965 → 2.099–2.218 / 0.778–0.783 | – | H42 | CRC α 2.915 | FA/cam-h / recall | GT | – | – | FACTS | as H42's conformal point, pre-H33b |
| 12 | 0/10 vs 6/10; cost −0.035 | [−0.037, −0.033] | H33 | CRC vs plug-in, α 2.915 | splits exceeding α / recall | GT | – | – | qualified (empirical B, R59) | "CRC held the FA target in 10/10 splits vs 6/10 for plug-in, for 3.5 points of recall — with an approximate B" |
| 13 | 2.312 / 0.789 | [2.265, 2.364] FA | H33 | CRC θ 0.960–0.963 | FA/cam-h / recall | GT | – | – | qualified (R59) | as #12 |
| 14 | floor 0.248–0.263 | – | H33 | α 0.001 | FA/cam-h | GT | – | – | FACTS; R27 | "our assumed 0.001 is uncertifiable from 338 simulated worlds (28 §6)" |
| 15 | B = 123.5 FA/cam-h | – | H33b | fixed in advance | FA/cam-h | GT | – | – | qualified (exact only for min(L, 123.5) until H33c; R60) | "B fixed in advance, valid once the per-visitor cap is enforced (H33c)" |
| 16 | θ 0.963436 → 2.187 / 0.783 | FA [2.168, 2.269] (held-out 2.216) | H33b / H45b | certified fixed-B | FA/cam-h / recall | GT | – | – | FACTS; R60 | "the fixed-B point, superseded by H33c" |
| 17 | 2.223 / 0.787, 10/10 | [2.178, 2.274] | H33c | capped, α 2.915 | held-out FA/cam-h / recall | GT | – | – | FACTS | "with the cap B is a real bound: held-out FA 2.223 ≤ 2.915 in 10/10 splits" |
| 18 | θ 0.9618 (0.961780) → 2.196 / 0.789 (284/360) | – | H33c | certified capped θ | θ / FA/cam-h / recall | GT | – | – | qualified (allowlisted rounding of 0.961780; FACTS range 0.9599–0.9628) | always with "B = 123.5 fixed in advance and a one-alarm-per-visitor cap" |
| 19 | 3.4 % | – | H33c | equal-θ FA cut from cap | % | GT | – | – | FACTS | "the cap is a validity fix, not an FA cut (3.4 %)" |
| 20 | 0.511 / 0.586 (util 0.88) | – | H45 | A1 θ 0.95 FIFO / ranked | realised @5 min | GT | H22 | operator | FACTS | "A1 at one operator" |
| 21 | 0.324 / 0.504 (util 0.95, 53 % bulk-acked) | – | H45 | pooled θ 0.9 | realised @5 min | GT | H22 | operator | FACTS | "never pooled θ 0.9: it floods the queue" |
| 22 | −0.083 | [−0.103, −0.064] | H45 | pooled − A1 ranked | realised @5 min | GT | H22 | operator | FACTS | as #21 |
| 23 | θ 0.962851 → 0.571 / 0.621, 92/h | ranked +0.035 [+0.016, +0.055] | H45 | conformal | realised @5 min | GT | H22 | operator | FACTS (superseded) | only as "H45's original point, before B was fixed" |
| 24 | 0.573 / 0.617, 90/h | vs A1 ranked +0.031 [+0.014, +0.050] | H45b | θ 0.963436 | realised @5 min | GT | H22 | operator | FACTS; R60 | "the fixed-B point realises 0.617 ranked" |
| 25 | **0.584 / 0.618, 90.6/h** | vs A1 ranked +0.032 [+0.014, +0.052] | H45c | θ 0.9618 capped | realised @5 min | GT | H22 | operator | FACTS (canonical ship point) | "ranked queue, one operator, invented operator model, GT uids: 0.618 at 5 min" |
| 26 | −0.015 (2 ops) / −0.031 (3 ops) | [−0.038, +0.008] / [−0.052, −0.011] | H45c | capped conformal − A1 ranked | realised @5 min | GT | K = 2, 3 (H22) | operator | 32 §H45c (decimals in FACTS) | "with ≥ 2 operators A1 θ 0.95 ranked" |
| 27 | 70.96 → 4.20 | [63.80, 78.30] / [3.84, 4.57] | H40 | naive N → gated + context C | FA/cam-h | GT tracks + assumed noise | – | tracker noise (0.3 m, fragments, ghosts) | qualified (FA optimistic: no twins) | "gating cuts naive line-cross FA 70.96 → 4.20, assumed tracker noise" |
| 28 | recall@10 0.945 → 0.100 | [0.060, 0.145] | H40 | N → C | recall@10 | GT | – | noise | FACTS (not met) | "depth gate killed intruders who stop at the edge" |
| 29 | clean FA 0; recall@10 0.782 | [0.736, 0.829] | H40b | C | FA/cam-h / recall@10 | GT | – | noise | FACTS (not met, bar 0.9) | "0 clean FA in 3,002 cam-h but recall 0.782" |
| 30 | patrol 0.389 / maintenance 0.099 (twins 0.488) | [0.367, 0.412] / [0.088, 0.111] | H40b | C twins | FA/cam-h | GT | – | noise | FACTS; R50, R56 | "≈ 490× our assumed 0.001 budget" |
| 31 | shortfall 0.218 = 0.101 rule + 0.047 context + 0.070 noise | – | H40b audit | C | recall | GT | – | noise | FACTS; R50 | "rule 10, context 5, noise 7 points" |
| 32 | 0.488 → 0.0047, 99.0 % removed | [0.0023, 0.0075]; [98.5, 99.5] % | H53 | C → C+abc | twin FA/cam-h | GT, true positions | – | badge, BLE tag, PIDS all assumed | qualified (R55) | "context and a second sensor remove 99 % of authorised-crosser FA (H53), all sensors simulated, tailgater defeats it" |
| 33 | recall@10 0.782 → 0.758 (−0.023) | [0.710, 0.805] | H53 | C+abc | recall@10 | GT | – | sensors | FACTS (not met: bar demanded zero loss) | "at a 2.3-point recall cost" |
| 34 | tailgate 0.007; stolen tag 0.701 | – | H53 | C+abc | recall@10 | GT | – | sensors | FACTS | "the access log is blind to tailgaters" |
| 35 | 99.1 % (19 of 2,064) | [98.6, 99.5] | H54 | C+abc, estimated positions | % twin FA removed | GT (benign noise) | – | sensors, noise | qualified (upper bound, no ID switches) | "99.1 % with estimated positions — an upper bound" |
| 36 | recall 0.782 → 0.772 | – | H54 | C+abc est. | recall@10 | GT | – | sensors | FACTS | as #35 |
| 37 | **0.685** (61/89) vs 0.056 | [0.589, 0.778] | H54 | C+abcg (gate counter) vs C+abc | tailgater recall@10 | **GT** | – | sensors, gate counter | qualified (R61) | "0.685 with GT identities; 0.10 actor-aware under H59's ID switches" |
| 38 | removal 96.3 % (+0.019 FA/cam-h) | – | H54 | C+abcg | % | GT | – | sensors | FACTS | "the counter costs 3 points of twin removal" |
| 39 | 99.1 % at both rates | [98.7, 99.5] | H59 | C+abc | % twin FA removed | tracker (157.6 / 472.7 IDSW/track-h) | – | sensors, ID switches | FACTS | "twin removal survives ID switches" |
| 40 | **0.100** (benign 0.769) | [0.071, 0.131] | H59 | C+abcg calibrated | tailgater recall@10, actor-aware | tracker | – | ID switches | qualified (scoring artefact, R61) | "the actor-aware score drops to 0.10 because the alarm is credited to the swapped label" |
| 41 | 0.108 / 0.100 | – | H59 / reconciliation | C / C+abcg calibrated | actor-aware recall | tracker | – | ID switches | FACTS | "C alone collapses too — denominator, not fusion" |
| 42 | 0.828 / 0.739 | – | TAILGATER_RECONCILIATION | C / C+abcg | label-agnostic (window-only) recall | position-free | – | ID switches | derived (audit) | "the fused decision is unchanged (0.83 / 0.74 label-agnostic)" |
| 43 | 0.685 / **0.715** / 0.725; false-credit 14.8 / **31.3** / 49.3 % | – | H62 | C+abcg, r = 1/2/3 m | position-time recall | position | – | ID switches | FACTS (diagnostic only, principle 4) | "0.715 at 2 m but 31.3 % bystander false-credit — a diagnostic, not a scorer" |
| 44 | 0.711 vs 0.701 | – | H62 | C+abcg benign | position(2 m) vs actor-aware | GT | – | – | FACTS | "the two scorers agree with GT identities" |
| 45 | 0.901 / 0.802 / 0.727 | [0.872, 0.936] / [0.774, 0.830] / [0.706, 0.747] | H56 | 1 PTZ, H39 calib | acquire@3 s by range | GT | – | all PTZ timings assumed | FACTS | "with assumed PTZ timings, far acquire 0.727" |
| 46 | missed second 0.369 vs 0.057 | [0.325, 0.406] / [0.043, 0.070] | H56 | 1 vs 2 PTZs @120/h | fraction | GT | – | PTZ timings | FACTS | "one PTZ is busy 0.382 of the time" |
| 47 | 0.027 | [0.010, 0.047] | H63 | naive "looks like a guard → suppress" | recall@10 | GT roles | – | sensors, roster, role classifier | FACTS | "appearance is not identity: 0.027" |
| 48 | 0.745 at twin FA 0.018 | [0.694, 0.794] / [0.014, 0.024] | H63 | corroboration mismatch | recall@10 / FA/cam-h | GT roles | – | sensors | FACTS (not met) | "corroboration mismatch 0.745, 96 % of C's ceiling" |
| 49 | 0.198 | – | H63 | + 5 m patrol-route prior | recall@10 | GT | – | sensors | FACTS | "route priors hurt: intruders walk plausible routes" |
| 50 | 0.740 → 0.700 (drop 0.040) | [0.020, 0.062] | H63b | live rule b, body-keyed | recall@10 | tracker | – | sensors, ID swaps | qualified (R64: role cached at track birth) | "as run 0.040; with the role re-drawn per alarm 0.007 (C 0.761)" |
| 51 | naive 0.028 → 0.249 | – | H63b | a | recall@10 | tracker | – | – | R64 (artefact of caching) | never without "cached at track birth; re-drawn per alarm it stays 0.027" |
| 52 | 0.007 (C 0.761) | – | AUDIT_H63B | b, role re-drawn per alarm, 3 seeds | recall drop | tracker | – | – | derived (audit rerun) | always with "once the role is re-drawn per alarm" |
| 53 | **0.690 → 0.486** (drop 0.203); k 8 0.600 | [0.667, 0.712] / [0.459, 0.514]; [0.179, 0.228] | H66 | FIFO, k = 0 → 16 decoys | realised @300 s | GT | H22 | operator, decoys | FACTS | "a 16-alarm decoy drops FIFO recall 0.690 → 0.486" |
| 54 | ranked 0.483 | – | H66 | ranked, k = 16 | realised @300 s | GT | H22 | operator (Beta stand-in scores) | FACTS | "ranking alone does not help" |
| 55 | 0.689 (0.538 as registered) | [0.666, 0.711] / [0.514, 0.563] | H66 | coincidence escalation, k = 16 | realised @300 s | GT | H22 | operator | qualified (R65) | "0.689 only with the post-registration bulk-ack exemption; 0.538 as registered, NOT met" |
| 56 | exemption share 0.151; 0.001 escalations/cam-h | – | AUDIT_H66 / H66 | escalation | recall / rate | GT | H22 | operator | FACTS | "0.151 of the recovery is the exemption — a procedure" |
| 57 | 0.704 / 0.697 / 0.700; (c) − (a) −0.004 | [0.682, 0.727] / [0.673, 0.719] / [0.676, 0.725]; [−0.020, +0.011] | H70 | pooled / per-site / re-allocated θ, K = 2 | realised @300 s | GT | K-wall | estate, σ_δ 0.3 declared | by construction (R67) | "flat recall is by construction: one declared score model at every site" |
| 58 | util 0.842 (K 2) / 0.563 (K 3) | – | H70 | K-wall | util | GT | K-wall | estate | by construction (same recall) | "K = 3 buys resilience, not recall" |
| 59 | worst site 1.622 / 0.551 / 0.914; ≈ 3.3 sites > 2B | – | H70 | (a) / (b) / (c), B = 0.5 | FA/cam-h | GT | – | estate | FACTS | "one pooled θ keeps the estate on budget while ~3 sites run above 2B" |
| 60 | ×3 in 24 h: 1.0 / 1.0 / 0.133; ×2 0.97, ×1.5 0.32 | – | H70 / AUDIT_H70 | per-site vs estate-total monitor | detection prob. | GT | – | estate | FACTS; 0.32 [derived] | "a per-site daily check reliably catches ×2 or more" |
| 61 | daily ×1.5 in 48 h 0.975 (×1.25 0.394) | – | H70b | per-site θ, daily Poisson | detection prob. | GT | – | estate | FACTS | "a ×1.25 drift is caught only 0.394 of the time" |
| 62 | CUSUM ×1.5 0.996 at 0.020 false flags/site-week (0.0198); delay 13 vs 26 h | [0.995, 0.997] / [0.017, 0.023] | H70b | CUSUM | detection / false flags | GT | – | estate | qualified (R69, marginal) | "on our 0.02 bar — marginal; a re-run gives 0.0206" |
| 63 | pooled − per-site ×1.5 −0.147; −0.034 / −0.159 / −0.384 at σ_δ 0.15 / 0.3 / 0.6 | [−0.156, −0.139] | H70b / AUDIT_H70B | pooled θ cost | detection prob. | GT | – | declared σ_δ | by construction (set by σ_δ) | "the pooled cost is set by how different the sites are, which we declared" |
| 64 | flat CUSUM 0.896 / hour-of-day 0.032 | – | H70b | benign day/night | false flags/site-week | GT | – | estate | FACTS (C3 fails) | "model the hour of day" |

**64 rows.**

## 2 · Which number to say when

1. Ship point → **conformal θ 0.9618 with B = 123.5 fixed in advance and a one-alarm-per-visitor cap**: 2.20 FA/cam-h, recall 0.789. Never θ without B; never 0.9629/0.963436 as the current point (R60).
2. Operator realised recall → **0.618 @5 min, "ranked queue, one operator"** (H45c), invented H22 operator, GT uids. Never 0.621 (H45, pre-B) or 0.511 (A1 FIFO) as the ship point.
3. A1 → "2.915 / 0.825, one of three H42 points" — never "A1 ships" (R48); ≥ 2 operators → A1 θ 0.95 ranked.
4. Pooled θ 0.9 → "5.033 / 0.894 — never at one operator: 0.504 ranked, −0.083 vs A1" (H45). Zero range is partly by construction (AUDIT_H42).
5. Conformal guarantee → "10/10 splits under α" only with "fixed B" (H33b/H33c); H33 alone is approximate (R59).
6. Budget ratios → always "over *our assumed* 0.001 (28 §6)" (R56).
7. Line-cross → "0 clean FA but recall 0.782, not met; twins 0.488 ≈ 490× our assumed budget" (H40b).
8. Fusion → "0.488 → 0.0047, 99 % of authorised-crosser FA, 2.3-point recall cost, all sensors simulated, tailgater defeats it" (H53, R55).
9. Tailgater → **0.685 always with "GT identities, 0.10 under H59"** — and "a scoring artefact; the fused decision is unchanged" (R61).
10. Position scoring → "0.715 at 2 m but 31.3 % bystander false-credit — diagnostic only" (H62).
11. Decoys → **H66 0.690 → 0.486** "as registered, 0.538 without the exemption" in the same sentence (R65); 0.689 never alone.
12. Estate → H70's flat recall "**by construction**" (R67); CUSUM "marginal, on the 0.02 bar" (R69); guard uniform drop "0.007 once the role is re-drawn per alarm" (R64).

## 3 · Cross-doc contradictions found (65 v2 §0/§3/§5, 101, 102, 105, 106, 108, 111, 00_INDEX) and fixes

| # | contradiction | where | fix applied |
|---|---|---|---|
| C1 | Whiteboard arithmetic gives the loiter operator line as "~92 alarms/h, realised 0.621 ranked (H45)" — the superseded pre-B point — while §0 item 1 and §3 make H33c/H45c (90.6/h, 0.618) canonical. | 65 v2 §5 arithmetic | Now "θ 0.9618 capped ⇒ ~91 alarms/h, realised 0.618 ranked (H45c)". |
| C2 | "The shipped policy is one pooled θ (H42)" (5.033 FA/cam-h) contradicts FACTS' operator-measured rule "never pooled θ 0.9" at 1 operator (H45) and the canonical conformal ship point. | 101 Q24, 101 P7 | Both now say pooled is H42's *selection* policy, but the operator-measured ship point is conformal θ 0.9618 at 1 operator, never pooled θ 0.9. |
| C3 | Same collision: "the sim's shipped policy is one pooled conformal θ" merges H42's pooled θ 0.9 with the conformal point. | 108 card A | Now "one conformal θ (0.9618, H33c) for the pooled site". |
| C4 | "the uniform rule is tracker-id keyed (0.007 loss, AUDIT_H63B)" drops the "role re-drawn per alarm" qualifier; the run's drop is 0.040 (R64). | 102 follow-up 2 | Qualifier added: "0.040 as run; 0.007 once the role is re-drawn per alarm". |

Consistent (no fix): 105 (H66/H63b/H70/H70b all carry R64/R65/R67/R69 qualifiers), 106 (0.618 / 0.584, K 0.842 / 0.563,
−0.015 match #25/#26/#58), 111 (0.538 as registered, H70 by construction). 00_INDEX step 11 ("120 → 92 alarms/h,
realised 0.511") is `74` Drill 1's pre-H45c arithmetic — read-only here; flagged, not edited.
