# AUDIT_84_85 · Cold-read review v3 (84) and defence context practicalities (85)

Audited 2026-09-27 against `5afcd04` (85) and `033bdbc` (84), from the reader's side of a MOD
programme lead. Method as AUDIT_67-69: every [V] source in `85` was re-fetched by WebFetch the
same day and the quote compared; each [A] was retried on an alternative primary URL; `84`'s
counts were recomputed by script. No GPU, editor or `survsim/` change.

## 1. 85: the eleven [V] sources re-fetched

| claim (85 §) | page | result |
|---|---|---|
| BPSS "recognised standard for the pre-employment screening…"; CTC 10 y (5 y non-FSC), SC 10 y (7 y non-FSC), DV 7 y; SC credit check; DV "full review of personal finances" (§1) | gov.uk NSV clearance levels | **[V]** all match. DV's 7 y is stated for non-FSC contractors with ongoing measures; 85 gives it without the qualifier (acceptable in a table) |
| OFFICIAL "good commercial solutions"; SECRET/TS "bespoke, sovereign protection" (§2) | gov.uk HMG Security Policy Framework (HTML) | **[V]**. Not on the Government Security Classifications landing page, which only lists the tiers |
| ISN 2023/02 FSC listed (§2) | gov.uk Industry Security Notices | **[V]**; full title adds "…and MOD Contracting Authorities" |
| military/dual-use definitions, "goods, software or technology (including data, information and technical assistance)", "criminal offence…" (§3) | gov.uk UK strategic export controls | **[V]**; penalties include imprisonment |
| DASA "finds and funds exploitable innovation"; "became part of UK Defence Innovation in February 2026" (§4) | gov.uk DASA organisation page | **[V]** confirmed verbatim |
| DEFCON 658 "applies to all suppliers down the supply chain" (§4) | gov.uk DEFCON 658 | **[V]**, but the `defence-condition-658-cyber` slug now 404s; the quote is on `…-cyber-flow-down` (edition 10/17, updated 13 Dec 2022). Source line annotated. Risk-profile mapping still not on the page ([X] stands) |
| Cyber Essentials "government-backed, industry-supported", "standard technical controls", "bid for government contracts" (§5) | gov.uk CE overview | **[V]** |
| DPA 2018 s.26 "(a) the purpose of safeguarding national security, or (b) defence purposes" (§6) | legislation.gov.uk | **[V]**; the "required for", provision-by-provision reading holds |
| Defence AI Strategy 15 Jun 2022; "effective, efficient, trusted and influential"; trust quote (§7) | gov.uk | **[V]** |
| Ambitious, safe, responsible, 15 Jun 2022 (§7) | gov.uk | **[V]** |
| STANAG definition (§8) | nato.int standardization topic | **[V]** verbatim |

## 2. 85: [A] items retried

| item | tried | move |
|---|---|---|
| Five AI ethics principles | ASR HTML (Annex A) | **[A]→[V]**: Human-Centricity, Responsibility, Understanding, Bias and Harm Mitigation, Reliability |
| Cyber Essentials Plus | ncsc.gov.uk/cyberessentials/overview | **[X]→[V]**: "The same protections, but with more rigorous, independent technical testing". CE+ required via DEFCON 658 risk profiles stays [A] |
| ITAR/EAR follow US-origin items | ecfr.gov (302 → unblock.federalregister.gov, bot-blocked); LII CFR text | **[A]→[V]** on the LII text: 15 CFR 734.3(a)(2) "All U.S. origin items wherever located", (a)(3) de minimis; 22 CFR 120.51 reexport incl. deemed reexport. Thermal-imager dual-use flag stays [A] |
| Vetting is sponsored | NSV page | **[A]→[V]**: "set by the departmental authority responsible for the post". Residency *years* stays [A]; the page says only "UK residency may affect the checks undertaken" |
| STANAG 4676 / 4607 | nso.nato.int (two URLs, 404); nato.int topic (no mention) | **stays [A]** — correctly caveated in 85 and Q9 claims no use |
| DASA → UK Defence Innovation, Feb 2026 | DASA org page | **confirmed [V]** |

## 3. 85: Q&As and tone

All ten Q&As trace to a section with a [V] source or are framed as "what to say" (Q4, Q7 point to
`33`/§9). One fix: **Q10** asserted the push *would be* "a DEFCON 658/Cyber Essentials breach",
a legal determination §0.3 forbids; now "could breach the company's … obligations". Nothing reads
as advice to misrepresent: §0 and Q1–Q2 steer to "I don't hold one; willing to be sponsored"; Q2's
red flag names gaming vetting. §9.4 correctly refuses "synthetic data makes the model export-free".

## 4. 84: fixes, timing, gap mirrors

**Spot-checked 9 of 15 frictions — all hold.** #1 no "38"/"39 numbers" left in 00/42/65 v2; 65 v2
§2 has 11b [40]. #2 60 and 65 v2 say HEAD `e231a4a`. #3 60 §H "The twin answer" exists. #4 60 §F
retitled. #5 21 numbered items in 60 carry ✗ (awk count). #6 65 v2 opener has the H53/H54 sentence
and "small, one site". #13 H15 carries its result in 46 and 52; "pre-registered, running" gone.
#14 42 Day 1 uses `68` §2 and `65` v2 §1a. #15 00 table: 60 2,445 words / 40 numbers, 35 arch, 77
superseded by 84.

**1-hour path word count, recounted by script** over the same sections (60 all; 65 v2 §1, §3–§7;
FACTS "The forty to know cold"; 33 §0 + §3; 80 §2–3; 84 §3–4): 2,445 + 2,047 + 1,187 + 612 + 518 +
668 = **7,477** ≈ the stated ~7,480. Row minutes sum to 58 ≤ 60.

**Five open gaps identical** in 84 §4, 65 v2 §4 and 78 §3: same five, same order (real-site alarms,
night, clothing-change identity, Jetson latency, drift certification), and the same four closed
items (H38, H45, H51, H53/H54). 65 v2's closed line omits the "99.1 % is an upper bound" qualifier
that 84 carries; its §6 Q4 has it, so not changed.

## 5. 4-hour path

With `85` (15b, 10 min) added the 4-hour steps summed to 250 min. **Trimmed step 13 (`17` system
design overview) from 20 to 10 min** — the nine-stage diagram only; step 8's `52` architecture
diagram already covers the prose, and `17` in full remains Day 1 of `42`. Now 60 + 180 = 240.
In `42`, Day 2 summed to 450 against a stated 435: block 10b cut to `85` §0 + §10 (10 min, §9
restates `52`/`47`) and the header corrected to 445 min.

## Scores

| file | sources | numbers/counts | honesty/tone | score |
|---|---|---|---|---|
| 85 | 11/11 [V] hold (one slug moved); 4 [A]/[X] → [V] | n/a | one legal-determination slip (Q10) fixed | **8.5/10** |
| 84 | n/a | 7,477 vs ~7,480; 9/9 fixes hold; gaps mirrored | accurate | **9/10** |
