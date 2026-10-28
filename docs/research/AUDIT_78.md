# AUDIT_78 · the vendor talk tracks, read as their CTO

> **Superseded in part (2026-09-27, AUDIT_LEDGER §10):** fix #3's retirement of 'context and a second sensor' was lifted after H53 in one qualified form only (AUDIT_H53, R55: H53 + simulated + tailgater on the same line).

Audited 2026-09-27 against `a46f190`. Method as AUDIT_67-69: every company claim re-fetched
(WebFetch, primary pages), every number grepped in `FACTS_VERIFIED.md`, retired registry checked.

**Score: 6.5/10 before → 9/10 after.** Two headline numbers in the 90-s opener were wrong or
misleading, and every product section opened with guesses at their architecture.

## 1. Company claims re-fetched

| claim | source | result |
|---|---|---|
| £3 m, Maven VCTs lead, Maven Cognition EIS + angels, 22 Sep 2026 | mavencp.com release | [V] |
| ">£5 m revenue… MOD and major defence contractors **across Europe and the US**" | same | [V] up to "contractors"; tail not returned on re-fetch → **dropped** |
| "designed to perform in challenging environments…" in quotation marks | same | [A] returned as summary → **de-quoted, marked paraphrase** |
| Luke Matthews, Partner at Maven; director 1 Jul 2026 | release + CH officers | [V] |
| Eccles-Williams director 3 Aug 2026; Livingstone also secretary; Blandy secretary 14 Aug 2025 | CH officers / filing history | [V]; "role not public"/"unexplained" commentary **removed** |
| SH01 1 Jul + 9 Sep 2026; Articles + resolutions 31 Jul 2026 | CH filing history | [V] |
| [vendor product]/[vendor product]/[vendor product] wording, "data-agnostic", "dollars… to cents" | /our-work/ | [V]; [vendor product] line completed ("low SWaP austere environments") |
| "Sovereign solutions, developed in the UK" | /what-we-offer/ (not /our-work/) | [V]; attribution fixed |
| ReconSphere, [vendor product], [vendor product] "performance management… and retraining" | /what-we-offer/ | [V] |
| CCTV/false alarms, behaviour modules, "the vendor ML Tech Suite" | /solutions-lab/ | [V] |
| MOD + primes; Leonardo Partner | /partnerships/ | [V] |
| RCO co-development, Ukraine data, degraded/camouflage/weather, FlyEye/FT-5/Warmate | Calibre | [A]; RCO/Ukraine absent from /our-work/ → [X] on the vendor pages confirmed |
| "first institutional funding round"; "interpret visual information in complex environments" | Diligency | [V] |

## 2. Numbers

All 40 figures found in FACTS; none matches a RETIRED pattern outside a correction. Misuses:

| # | where | problem | fix |
|---|---|---|---|
| 1 | §2 opener, §1.3 | H33 "held its target on 10/10 splits **versus 6 for the plug-in**" — FACTS: plug-in **exceeded** α in 6/10 (held in 4). Opener inverted the comparison | "never exceeded in 10; plug-in exceeded in 6"; CRC bounds expected per-world FA |
| 2 | §1.1 | "raw YOLOv8n 0.938 **on LLVIP**" — H32b 0.938 is on our undegraded night renders | corrected; "no night penalty quotable" |
| 3 | §2 opener | "the answer is context and a second sensor" — context (H58 D) missed P8 (≥ 25 %); second sensor unmeasured | "site context cut it by a fifth, still nowhere near" — **reinstated 2026-09-27 in qualified form only after H53** (AUDIT_H53; RETIRED_CLAIMS R55 allows the phrase only on a line with H53, simulated and tailgat…) |
| 4 | §1.6 | −20.7 % given without "vs GBM arm B, P8 failed" | added |
| 5 | §1.1 | H17 HOTA +0.0103 without the pre-parity-scorer caveat FACTS carries | added |
| 6 | §1.6 | "0.001 is uncertifiable" | FACTS wording: infeasible |

Opener re-checked: 0.276 → 0.152 (H1, 3 seeds), +0.012 (H14b +0.0121, 5 seeds), ~2,900× (A1
2.915 / 0.001, `23` M6), 10 splits / 6 / 0.035 (H33) — all FACTS, none retired.

## 3. "Don't claim" vs 77 §4 and audits
Consistent: [vendor product] (WA2), [vendor product] (WA3, no Jetson/SNN number), [vendor product] (WA2/WA5, H26/H34/H38 not
run), ReconSphere (H37 no number), [vendor product] (no fusion result), CCTV (WA1). Added a §1.6 "don't
raise" line (investors, directors, trade-press claims, product internals).

## 4. 30/60/90 vs `23`
Each item now carries its `23` rank and status. Fix: "M1 remainder: evaluator parity" — parity is
**done** (2026-09-27); remainder is `eval_det`/ReID profiling + manifest hashes. M8 rank 15 correct.

## 5. Tone
- Every "Likely [A]" block guessed internals ("CNN/transformer backbone with brain-inspired
  additions", "event-camera input", "runs on conventional GPUs", "slew-to-cue… track-level
  fusion"). To the people who built it this reads as reverse-engineering and is probably wrong
  somewhere. Replaced with "Public [V]" quotes; unknowns became questions.
- Opener said "your Ukraine set" — trade-press [A] claim about sensitive operational data,
  over-familiar in a first 5 minutes → removed (also from §1.1).
- Director commentary ("stays unexplained") removed; board row marked background only.
- "the way a CNI buyer scores them" → "the way i-LIDS scores them" (a sourced standard, not a
  claim about their customers).

Remaining [A]: [vendor product] as the closest product to SurvSim, and the CCTV line as the job's home —
both labelled as my reading.
