# AUDIT_H70B · Adversarial audit of H70b (per-site drift monitors)

Pre-registration b5074f8 (it also swept in four lines of another agent's H69-audit edit to 32 §H69; content
unaffected, commit hygiene only) → results 537b50e (order confirmed). Code `survsim/experiments/drift_monitor_scale.py`,
config `survsim/experiments/configs/h70b_drift_monitor_scale.yaml`, results `out/experiments/h70b/results.json`.
Re-run reduced: 3 seeds × 40 worlds × 40 sites, σ_δ ∈ {0.15, 0.3, 0.6}, bootstrap 1,000 (scratch, 19 min).

| # | Claim | Verdict | Fix |
|---|---|---|---|
| 1 | C1 met: CUSUM ×1.5 within 48 h 0.996 at 0.020 false flags/site-week | **Detection half robust, false-flag half a coin flip on the bar.** Full run 0.01975 [0.0168, 0.023]: the point clears 0.02 by 0.00025 and the CI straddles it. Re-runs: σ_δ 0.15 run 0.0206 (C1 **fails**), 0.3 run 0.0194, 0.6 run 0.0179. Not a tuned pass — h is calibrated on 2,000 fresh simulated null weeks at λ̂, never on the test weeks — but h targeted 0.01 and one-week λ̂ noise doubles the realised rate, which lands it on the bar. Also k is tuned to ×1.5 and tested at ×1.5 (matched shift, favourable). | 32/FACTS now say "C1 marginal: detection met, false-flag rate on the bar (CI straddles 0.02; one re-run fails)". R69. |
| 2 | h chosen on the same data it is tested on? | **No.** h from simulated nulls at the calibration-week λ̂; null and drift test weeks are fresh draws. | none |
| 3 | C2 fails: pooled θ costs −0.147 at ×1.5 | **Entirely set by σ_δ (an input), as the pre-registration said.** Pooled − per-site daily det48 at ×1.5: σ_δ 0.15 −0.034 (C2 **passes**, all Holm TOST p 0.004), 0.3 −0.159, 0.6 −0.384 (and −0.175 at ×2, −0.069 at ×3). The sign is robust; the size is whatever σ_δ is declared. | 32/FACTS carry "σ_δ 0.15 passes, 0.6 −0.38". |
| 4 | Holm TOST for C2 | **Sound but partly vacuous.** Bootstrap-tail TOST with Holm over 4 sizes is fine; at ×2/×3 both arms are at the ceiling (≈1.0), so equivalence there is automatic and C2 is really decided at ×1.25/×1.5. | noted |
| 5 | Hour-of-day fix post hoc? | **Pre-registered** as "reported, not decision-bearing" — not post hoc. But "fixes it" overstates: 0.032 per_site diurnal and 0.035 per_site flat are above the 0.02 bar; 24 hourly baselines from 7 samples each is structurally noisier than one flat λ̂, not just "calibration noise". | 32 reworded: "cuts 0.90 → 0.03, still above the 0.02 bar". |
| 6 | "CUSUM halves delay (26 → 13 h)" | **Holds at ×1.5 only as stated.** Median delay daily/CUSUM: ×1.25 61/47 h (−23 %), ×1.5 26/13, ×2 19/5, ×3 15/3. So it does *more* than halve at ×2/×3 and does not halve at ×1.25. Caveat: CUSUM runs at 0.020 false flags vs the daily 0.014, and the daily check can only fire at day boundaries (a structural ~12 h median wait). | 32 carries the full row. |
| 7 | Analytic curve | **Correct.** First check sees 24 + f(d−1) hours-equivalent for phase f ∈ 1..24, second check a full drifted day, third is beyond 48 h; critical count = Poisson isf(0.001, 120) + 1; null 7 × tail = 0.0065/site-week. Sim vs analytic max |diff| 0.010. | none |
| 8 | Contradiction with H70's audited sentence ("per-site check only reliably catches drifts of about ×2 or more") | **Scope clash, not an error.** AUDIT_H70's derived 0.323 at ×1.5 is a single hour-96 check with 12 h drifted; H70b gives the daily check 48 h (two checks), which catches ×1.5 0.975. Both true; the H70 sentence must say "in one check". | 65 §0 item 21 line appended. |
| 9 | Figure / FACTS row | Figure matches results.json. FACTS row said "(C1 met)" unqualified. | FACTS row edited. |

## Retired / qualified
- R69: H70b "C1 met" without the marginal false-flag qualifier.

## Honest interview sentence
*In a simulated 40-site estate with per-site monitors everywhere, a CUSUM on hourly alarm counts catches a ×1.5
alarm-rate drift within two days almost always and in about half the time of a daily count check, but only at a
false-flag rate sitting right on our 0.02/site-week bar, and a flat CUSUM alarms on an ordinary day/night cycle
unless it models hour of day; how much a pooled threshold hurts drift detection is set entirely by how different
the sites are, which we declared rather than measured.*
