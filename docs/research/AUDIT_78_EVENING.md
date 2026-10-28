# AUDIT_78_EVENING · Evening staleness pass on `78`

Audited 2026-09-27 against the current evening's results (65 v2, 32, 38, 58, 73, 84, FACTS_VERIFIED).

1. Opener tailgater sentence was not byte-identical to `65` v2 §1a — H59 wording rewritten to match exactly.
2. Tracker product had no H24/H46b recommendation at all — added ByteTrack + OSNet-ImageNet at w ≈ 8, cross-validated, IDSW cost stated, never appearance-only.
3. Added the H46b night arm caveat (ΔAssA CI still touches 0) next to the new tracker sentence — not a met/positive result.
4. Edge/H38 line was missing H43/H43c entirely — added Percentile/QAT recovery (~41–44 %, below the 50 % bar) and flagged H43d as running, unresolved.
5. 90-day plan's Jetson-latency bullet updated to name H43/H43c/H43d instead of a bare "H43 is the on-device version".
6. [vendor product] §1.5 stated the H54 tailgater 0.685 recall with no H59 caveat — RETIRED_CLAIMS R61 violation; added the ID-switch collapse to 0.10 and the label-agnostic 0.83/0.74 reconciliation.
7. [vendor product]'s H34 drift line said "registered, runner uncommitted, no number" — H34 has run and is INCONCLUSIVE; replaced with the real PSI/KS/z_cal/embedding numbers.
8. 90-day plan's dose/night/clothing bullets didn't name H61/H62/H36/H29 — added each hypothesis number next to its roadmap item (M4/M16/M15).
9. Dose (H51/H52), calibration (H39/H56), forensic search (H37 pre-registered-only) and "don't claim" lines already matched current status — no change needed there.
10. Doc tests `test_docs_retired_claims.py` and `test_docs_numbers_in_facts.py` pass (10/10); `/tmp` is 12 GB, well over budget, but nothing in it is clearly safe to delete without risking another session's or VM's data — flagged, not deleted.
