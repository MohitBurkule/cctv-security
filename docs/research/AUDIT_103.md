# AUDIT_103 · adversarial audit of 103_SIM2REAL_AND_NIGHT_HONEST_STATUS.md (2026-09-28)

Every number checked against `FACTS_VERIFIED.md` and `RETIRED_CLAIMS.md` (R01–R66). No retired value found.

| # | Where | Was | Finding | Fix |
|---|---|---|---|---|
| 1 | §1a ReID-model row, [LIT] | "StrongSORT/BoT-SORT gain from ReID ([LIT] FACTS §18 rows)" | [LIT] with no URL; FACTS has no with/without-ReID delta | StrongSORT++ MOT20 HOTA 62.6 (arxiv.org/pdf/2202.13514), BoT-SORT-ReID 63.3 (github.com/NirAharon/BoT-SORT); "no delta quoted" |
| 2 | §1a, §2 line 4 | IDSW cost "+15.80 at w=8" beside the +0.0479 held-out result | +0.0479 is w=16 (chosen on day); its MOT20-02 IDSW cost is +33.4 (FACTS H46b) | both costs stated; w=1 named as shipped default |
| 3 | §2 line 3 | "reverse direction holds too" | unquantified; the reverse is w=8 → day +0.0570 | number and direction stated |
| 4 | §1a verdict, §2 line 6, one-sentence | "a design choice holds on real footage", "proven on one real site", "Design decisions do" | overclaim: one sequence (MOT20-02), 5 checkpoints, one decision | "held on one real sequence", "One design decision did", IDSW cost named |
| 5 | §2 line 5 | "It does not help association (H17)" | H17 is pre-parity, AssA n.s.; absence of evidence | "No association gain was shown (H17, pre-parity scorer)" |
| 6 | §2 night line 5 | "−0.47 to −0.84" | −0.84 is a rounding of −0.835 | "−0.470 to −0.835" |
| 7 | §1b "Why?" | luma 90 vs median 34 | 34 is not a FACTS row (source `69` §7 / CLAUDE.md) | tagged "not a FACTS row" |
| 8 | §4 probe 5 | "lifts AssA across sets" | IDSW numbers missing | +15.80 / +33.4 added |
| — | licences | KAIST / FLIR ADAS **[UNVERIFIED]** | kept unsoftened; MOT/LLVIP NC kept | none |
| — | other numbers | M1, 0.443/0.559/0.466, 0.5060/0.5268, H17, H24, H46b, H20, crowd stats, H32a/b, night arm, [LIT] URLs | all match FACTS | none |
