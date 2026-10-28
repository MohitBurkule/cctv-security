# 85 · Defence context practicalities: clearance, export control, procurement, standards

What a CV engineer joining a defence-AI SME (the vendor, `33`) needs on day one
that is *not* computer vision: vetting, classification, export control, how MOD
buys, cyber baselines, data law in a defence setting, AI policy, and NATO track
standards. Written 2026-09-27. WebSearch was exhausted; every [V] below was
read by WebFetch on the cited gov.uk / legislation.gov.uk / nato.int page that day.

Tags: **[V]** read on the primary page · **[A]** stated from general knowledge
or a page that only listed it; check before quoting · **[X]** tried and failed
(page 404 / did not contain the claim).

Cross-refs: `33`/`34`/`35` (company), `62` (site context), `38` (edge, JSP 936),
`44` (UK GDPR/DPA, DPIA), `47` (asset licensing), `59` (assurance), `67` §4–6, `78`.

---

## 0. The three things never to claim

1. **Never claim a clearance you do not hold** — not "clearable", "basically SC",
   nor "I had BPSS at X" unless you can name it. Say what you hold (likely
   nothing) and that you are *eligible and willing* to be sponsored.
2. **Never speculate about classified or customer sites** — not which bases,
   CNI operators or programmes the vendor serves beyond what `33` sourced
   publicly. "I've only read the public material" is the full answer.
3. **Never claim a legal/regulatory determination** — that SurvSim, a model, or
   a dataset "is not export controlled", "is exempt", or "is GDPR-compliant".
   Those are rulings for the company's export-compliance officer / DPO. You can
   say *why* synthetic data reduces the exposure.

---

## 1. Security vetting (National Security Vetting, UKSV)

Source: gov.uk "National security vetting: clearance levels" [V].

| Level | What it gives (quoted/paraphrased from the page) | Review | Notable checks |
|---|---|---|---|
| **BPSS** | "the recognised standard for the pre-employment screening of individuals with access to government assets"; OFFICIAL plus exceptional supervised SECRET access [V] | — | identity, right to work, employment history, unspent criminal records [V] |
| **CTC** | posts near at-risk public figures, terrorist-sensitive info, restricted military/commercial sites [V] | 10 y (5 y non-FSC contractors) [V] | Security Service checks [V] |
| **SC** | long-term frequent uncontrolled access to SECRET; occasional supervised TOP SECRET [V] | 10 y (7 y non-FSC contractors) [V] | adds credit/financial checks [V] |
| **DV** | frequent uncontrolled TOP SECRET / codeword [V] | 7 y [V] | Investigating Officer interviews, referees, "a full review of personal finances" [V] |

**Why an interviewer raises it.** Deployed-site work (camera surveys, on-site
debugging, access to real footage) may need BPSS at minimum and CTC/SC for some
sites. Vetting is **sponsored** — "The requirement for National Security Vetting (NSV) at any clearance
level is set by the departmental authority responsible for the post" [V, re-fetched
by `AUDIT_84_85`]; the employer/customer sponsors it for a post. Residency: the page
says only that "UK residency may affect the checks undertaken" [V]; a specific
number of years is [A — check UKSV guidance].

**Say:** "I don't hold a clearance. I'm happy to go through BPSS/SC when a post
needs it; nothing in my background I'm aware of would block it." **Don't say:**
"I'll definitely pass", or speculate about DV.

## 2. Classification and facility security

- **Government Security Classifications**: OFFICIAL, SECRET, TOP SECRET
  (OFFICIAL-SENSITIVE is a handling marking within OFFICIAL). OFFICIAL "can be
  managed with good commercial solutions"; SECRET/TOP SECRET need "bespoke,
  sovereign protection" [V, HMG Security Policy Framework page].
- **Facility Security Clearance (FSC, the successor term for "List X")**: a
  company site accredited to hold classified material. MOD policy is ISN 2023/02
  "MOD Facility Security Clearance (FSC) policy and guidance for UK Defence
  contractors" [V as listed on the Industry Security Notices page; the FSC
  guidance page itself 404'd → content [X]]. Note the vetting page's
  "non-FSC contractors" review periods (§1) — FSC status changes staff obligations [V].

**Relevance:** most SME R&D and nearly all CV development happens at OFFICIAL.
Real footage from a customer site may be OFFICIAL-SENSITIVE or higher and may
never leave that site. That shapes the ML workflow (§7).

## 3. Export control

Source: gov.uk "UK strategic export controls" [V].

- Two list families: **military** ("specially designed or modified for military
  use") and **dual-use** ("can be used for both civilian and military
  applications") [V].
- Covers "goods, software or technology (including data, information and
  technical assistance)" — i.e. **intangible transfers**: emailing code, a model
  file, a git push to an overseas server, or a technical briefing to a foreign
  national can be an export [V].
- "It is a criminal offence to export controlled items without the correct
  licence"; penalties up to custodial sentences [V].
- **US-origin parts** (e.g. certain sensors, thermal cores, Jetson modules):
  US **ITAR/EAR** can follow the item ("re-export") regardless of UK licensing
  [V, `AUDIT_84_85`: 15 CFR 734.3(a)(2) "All U.S. origin items wherever located"
  are subject to the EAR, (a)(3) foreign-made items above *de minimis* US content;
  22 CFR 120.51 defines ITAR reexport incl. a "deemed reexport" of technical data —
  read on the LII text of the CFR because ecfr.gov bot-blocks (302 to
  unblock.federalregister.gov)]. Thermal imagers above certain specs are a
  classic dual-use flag [A].

**Say:** "I'd assume a trained model and the tooling around a defence product
can be controlled technology, so I'd follow the company's classification and
not push code or weights anywhere without checking." **Don't say:** "It's just
open-source PyTorch, so it isn't controlled" — classification depends on what
the item *is/does*, not its framework.

## 4. How MOD buys (procurement)

- **DASA** "finds and funds exploitable innovation"; it "became part of UK
  Defence Innovation in February 2026" [V, gov.uk DASA org page]. Don't call
  DASA a standalone body in present tense.
- **Dstl** — MOD's science lab; publishes SAPIENT proto files and Stone Soup
  (see `37`) [V via `37`].
- **DEFCONs** — standard MOD contract conditions. **DEFCON 658** (cyber) "applies
  to all suppliers down the supply chain", with sub-contractor, records and audit
  obligations [V, gov.uk page]; it links to the Defence Cyber Protection
  Partnership risk profiles — that mapping was **not** on the page [X]. Def Stan
  05-138 is covered elsewhere in the corpus (`38`).
- **Crown Commercial Service** frameworks — cross-government buying routes
  [A]. **JSP 940** — not verified; don't name it [X].

**Why it comes up:** an SME's roadmap follows funding calls and contract
milestones; engineers write parts of technical proposals and trial reports.

## 5. Cyber baselines

- **Cyber Essentials**: "a government-backed, industry-supported scheme"; "a set
  of standard technical controls"; a current certificate is needed to "bid for
  government contracts" handling certain data [V, gov.uk overview].
- **Cyber Essentials Plus**: "The same protections, but with more rigorous,
  independent technical testing" [V, ncsc.gov.uk/cyberessentials/overview,
  `AUDIT_84_85`]. That MOD contracts often require CE+ via DEFCON 658 risk
  profiles is still [A].

**Engineer-level practice:** MFA, patched machines, no personal cloud for
company data, no unapproved LLM/SaaS for customer material.

## 6. Data protection in defence

- DPA 2018 **s.26**: UK GDPR provisions listed in s.26(2) do "not apply ...
  if exemption from the provision is required for (a) the purpose of
  safeguarding national security, or (b) defence purposes" [V, legislation.gov.uk].
- It is a *required-for* test applied provision by provision, not a blanket
  switch-off [V from wording]. Commercial CNI security (a private operator's
  CCTV) is normally ordinary UK GDPR/DPA territory with a DPIA (`44`) [A].

**Say:** "Even where a defence exemption might apply, I'd still design as if a
DPIA were needed — minimise, retain briefly, log access." **Don't say:** "Defence
is exempt from GDPR."

## 7. Defence AI policy lineage

- **Defence AI Strategy**, MOD, **15 June 2022** — "effective, efficient,
  trusted and influential"; trust via "safety and reliability of our AI systems,
  and our clear commitment to lawful and ethical AI use" [V].
- **Ambitious, safe, responsible** — policy paper, same date (15 June 2022) [V];
  its Annex A carries the MOD's five AI ethics principles: Human-Centricity,
  Responsibility, Understanding, Bias and Harm Mitigation, Reliability [V, HTML
  version of the paper, `AUDIT_84_85`].
- **JSP 936 Part 1 "Dependable AI in Defence"**, 13 Nov 2024 — the directive that
  operationalises the above: lifecycle assurance, "appropriate human
  involvement" [V via `67`/`38`]. See `59` for how our audit trail maps onto it.

## 8. NATO standards for sensor data

- **STANAG**: "a NATO standardization document that specifies the agreement of
  member nations to implement a standard ... to meet an interoperability
  requirement" [V, nato.int].
- **STANAG 4676** (NATO ISR tracking standard, track data) and **STANAG 4607**
  (GMTI radar format) [A — no nato.int text; `AUDIT_84_85` also tried two
  nso.nato.int catalogue URLs (both 404) and the nato.int standardization page
  (no mention); many STANAG texts are not public]. Relevance: if a customer fuses our tracks with radar/C2 systems, the
  output track schema may be dictated. SAPIENT/BSI Flex 335 (`37`) is the UK
  sensor-to-fusion interface we actually verified.

**Say:** "I know SAPIENT concretely; I'd map our track messages to 4676 if a
customer needed it." **Don't say** you have implemented either.

---

## 9. Why synthetic data matters under these constraints

1. **Real footage rarely moves.** Classified or OFFICIAL-SENSITIVE site footage
   stays on site (§2); a developer off-site cannot iterate on it. SurvSim
   scenarios are **unclassified stand-ins**: same geometry types (`62`), same
   behaviours and hard negatives, no real people.
2. **No personal data → no DPIA for the dev set.** Rendered people are not data
   subjects, so the training/eval loop avoids the UK GDPR burden (`44`), while
   the *deployed* system still needs its DPIA.
3. **Asset licences are the new constraint** — `47`: MetaHuman, SMPL-X/BEDLAM and
   Mixamo terms forbid ML or surveillance use; the CC0 Quaternius stack is the
   compliant default, and each set writes `licences.json`. Getting this wrong is
   a supply-chain problem for a defence customer.
4. **Export-friendly iteration.** Scenario YAML and synthetic sets can be shared
   with partners more easily than site footage — but the *trained model* may
   still be controlled technology (§3). Don't claim synthetic data makes the
   model export-free.
5. **Honest limit:** synthetic evaluation does not substitute for on-site
   acceptance (`84` §4 open gap: real-site alarms). Final numbers come from
   cleared staff on site.

---

## 10. Ten Q&As with red flags

**Q1. Do you have security clearance?** — "No. I'm willing to be sponsored for
BPSS/SC." Red flag: Implying you have or once had it.

**Q2. Would you pass SC?** — "I'm not aware of anything that would stop it;
it's sponsored, with financial and records checks." Red flag: "Definitely", or asking
how to game it.

**Q3. Can you take the model home to work on it?** — "Not without checking its
export and classification status; software and technical data count as
exports." Red flag: "It's just weights."

**Q4. Who do you think our customers are?** — Only what `33` sourced publicly;
"I'd expect to learn the rest after joining." Red flag: Naming bases or programmes.

**Q5. Is GDPR relevant if the customer is MOD?** — "DPA s.26 allows exemption
where *required* for national security/defence, provision by provision; CNI
commercial sites are normal UK GDPR, so I'd default to DPIA discipline." Red flag:
"Defence is exempt."

**Q6. What's DASA?** — "MOD's innovation funder; it became part of UK Defence
Innovation in Feb 2026." Red flag: Describing it as current standalone body.

**Q7. How does your simulator help with data we can't share?** — §9 points 1–2,
then point 5's limit. Red flag: "Synthetic data replaces field trials."

**Q8. What policy governs AI in defence?** — "Defence AI Strategy and Ambitious,
safe, responsible (June 2022), operationalised by JSP 936 Part 1 (Nov 2024)."
Red flag: Inventing JSP numbers.

**Q9. Have you worked with STANAG 4676?** — "No; I know SAPIENT/BSI Flex 335
from Dstl's proto files and would map to 4676 on demand." Red flag: Claiming field use.

**Q10. A colleague asks you to push to a personal GitHub for convenience.** —
"No — that could be an unlicensed export and could breach the company's
DEFCON 658/Cyber Essentials obligations; use company infra." Red flag: Treating it as a convenience question.

---

## Sources (fetched 2026-09-27)

- gov.uk — National security vetting: clearance levels [V]
- gov.uk — HMG Security Policy Framework [V]
- gov.uk — Industry Security Notices (lists ISN 2023/02 FSC) [V]; FSC guidance page 404 [X]
- gov.uk — UK strategic export controls [V]
- gov.uk — Defence and Security Accelerator organisation page [V]
- gov.uk — Defence Condition 658 (cyber) [V] (on re-fetch the `defence-condition-658-cyber` slug 404s; the quote is on `defence-condition-658-cyber-flow-down`)
- gov.uk — Cyber Essentials scheme overview [V]
- legislation.gov.uk — Data Protection Act 2018 s.26 [V]
- gov.uk — Defence Artificial Intelligence Strategy [V]
- gov.uk — Ambitious, safe, responsible [V]
- nato.int — Standardization (STANAG definition) [V]
- ncsc.gov.uk — Cyber Essentials overview (CE+) [V, added by AUDIT_84_85]
- law.cornell.edu (LII) — 15 CFR 734.3; 22 CFR 120.51 [V, added by AUDIT_84_85; ecfr.gov bot-blocked]
- nso.nato.int — STANAG 4676 catalogue lookups, 404 [X]
- MOD Cyber Security Model supplier guide — 404 [X]
