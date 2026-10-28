# AUDIT_92 · Verifying `92`'s pack/pocket fixes and its own recount

Audited 2026-09-27 against `92_COLD_READ_REVIEW_V4.md` (commit `182b06e`), `65` v2 §1/§3/§4, `60`,
`78` opener/§3, `73` §3, `38` §2.5, `58` §8.4, `52` §5b, `RETIRED_CLAIMS.md`, `tools/interview_pack.py`,
`tools/interview_pocket.py`.

1. **Pack/pocket PDFs re-extracted with `pdftotext -layout`** and diffed against the six canonical
   sentences (90/30-s opener, ship (H33c/H45c), tracker (H24/H46b, w ≈ 8), edge (H38/H43c),
   fusion+tailgater (H53/H54/H59), H52/H61). All six are present, carrying the required caveats
   (H59's 0.10 actor-aware collapse next to every 0.685; H52/H61's "labels on people, not
   background" framing) — `92`'s two fixes (pocket's tailgater H59 caveat, `78`'s stale H61 line)
   already landed at `182b06e` and hold. `R55`/`R61` regex checks against the extracted text found
   no unqualified `0.685` or unqualified "context and a second sensor" occurrence in either PDF.
   No generator-source change was needed; `tools/interview_pack.py`/`tools/interview_pocket.py`
   were not touched.
2. **`92`'s 8,235-word recount reproduced independently** by a fresh script over the same named
   sections (`65` v2 §1 + §3–§7, `FACTS_VERIFIED.md`'s "forty to know cold" block, `33` §0+§3, `80`
   §2–3, `84` §3–4, `60` in full): **8,262 words**, 0.3 % higher — the difference is entirely
   section-boundary rounding (60's full-file count differs by 32 words depending on whether a
   trailing table row is included; 80 §2–3 by 6; the rest match `92`'s per-section numbers to
   within 1 word). Same conclusion: ≈ 41 min reading + 7 aloud + 6 recall ≈ 54 min, under the
   55-minute ceiling. `docs/research/00_INDEX_AND_READING_ORDER.md`'s "1-hour path" line still said
   the stale `84`-era ~7,480 words / 37 min; updated to `92`'s 8,235 / 41 min (54 min total).
3. **The five open gaps** in `92` (real-site alarm numbers, night, clothing-change identity,
   Jetson latency, drift certification) are the same five, same order, as `84` §4, `65` v2 §4 and
   `78` §3 — confirmed by direct comparison, no drift.
4. **The five questions** in `92` are each traceable to a fact reviewed in this pass: Q1/Q2 to
   H59's tailgater reconciliation and the H33c/H45c cap; Q3 to H43d's checkpoint-dependent
   refutation; Q4 to the five open gaps themselves; Q5 to `RETIRED_CLAIMS.md` and
   `tests/test_docs_retired_claims.py` (which catch stale numbers, not stale verdicts — the class of
   drift Q5 asks about).

**Doc tests:** `test_docs_retired_claims.py` and `test_docs_numbers_in_facts.py` pass.

**`/tmp`:** the session scratchpad directory is inside a pre-existing `/tmp` tree already at ~12 GB
from unrelated prior sessions (paper-extraction `.txt` files, none of them from this task). Nothing
was added there beyond two small `pdftotext` outputs (`pack.txt`, `pocket.txt`, ~600 lines total).
Not cleaned — deleting other sessions' files without knowing what still needs them risks losing
work; flagged again as `AUDIT_78_EVENING` did.
