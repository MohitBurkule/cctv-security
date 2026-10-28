# 44 — Privacy law and ethics for CCTV analytics (UK / EU)

*Interview-prep dossier. Written 2026-09-26. Every factual statement carries a
source tag [Sn]; the source list at the end gives the URL and the date it was
fetched. Anything that is my reasoning rather than a quoted rule is tagged
**[INF]**. I am not a lawyer and this is not legal advice — it is what an ML
engineer at a surveillance-analytics company should be able to say fluently and
accurately in an interview, and where the edges of that knowledge are.*

---

## 0. Why this matters for the interview, and for SurvSim

the vendor sells computer vision into security and defence. An interviewer
from that world will probe three things: (1) do you understand that the legal
question is almost never "is this AI allowed?" but "is *this processing, for
this purpose, by this controller* necessary and proportionate, and can you show
your working?"; (2) do you know which features of a video-analytics product
tip it from ordinary personal data into *biometric special-category data*; and
(3) do you have a reflexive, recitable process — DPIA, retention, access,
audit — rather than vibes.

SurvSim has two specific exposures that this document surfaces, and that I
did not know about before writing it:

1. **The MetaHuman licence appears to prohibit exactly what SurvSim is for.**
   Epic's own licensing FAQ says you "may not use MetaHuman characters or
   animation curves to build or enhance any database or train or test
   artificial intelligence, machine learning, deep learning, neural networks,
   or similar technologies" [S13]. §8 unpacks this. It is the single most
   important finding in this report.
2. **Multi-camera re-identification is the feature most likely to be
   argued to be biometric processing.** The legal test turns on *purpose* —
   "for the purpose of uniquely identifying a natural person" [S4] — and a
   ReID system's purpose is, arguably, exactly that. §4 sets out both sides.

---

## 1. The UK legal stack for CCTV analytics

### 1.1 The instruments

| Instrument | What it does for CCTV analytics | Source |
|---|---|---|
| UK GDPR | General processing regime for non-law-enforcement controllers (retailers, estates, transport operators, most private security). Article 9 prohibits processing of "biometric data for the purpose of uniquely identifying a natural person" unless a 9(2) condition applies. | [S4] |
| Data Protection Act 2018 | Supplements UK GDPR (Schedule 1 supplies the domestic-law conditions for Art 9(2)(b), (g), (h), (i), (j)); Part 3 is the separate law-enforcement regime (police); s.205 carries the biometric definition. | [S2], [S4] |
| Data (Use and Access) Act 2025 (c. 18) | Amends the regime: Schedule 4 "Lawfulness of processing: recognised legitimate interests", s.80 "Automated decision-making", Part 6 "The Information Commission" (replacing the Commissioner with a Commission). | [S16] |
| Surveillance Camera Code of Practice (amended code laid 16 November 2021, in force 12 January 2022) | 12 guiding principles. Binding "have regard to" duty for relevant authorities (police, local authorities); voluntary good practice for everyone else. | [S1] |
| Human Rights Act 1998 / ECHR Art 8 | For public authorities: any interference with private life must be "in accordance with the law" and proportionate — the ground on which *Bridges* was won. | [S3] |
| Equality Act 2010 s.149 (PSED) | Public authorities must have due regard to discriminatory impact — the other ground on which *Bridges* was won. | [S3] |

The ICO's own video-surveillance guidance now carries the banner that, due to
changes made by the Data (Use and Access) Act, the guidance "is under review
and may be subject to change" [S5][S7]. **Say this in an interview**: it shows
you know the guidance is moving, and it means any answer pinned to a specific
paragraph of ICO guidance should be caveated.

The ICO guidance's scope explicitly covers more than fixed CCTV: ANPR, facial
recognition technology, body-worn video, drones, smart doorbells and action
cameras [S5]. Its framing sentence is worth memorising in spirit: surveillance
should be seen not as "the cure to the problems that organisations may face.
But instead, a helpful supporting tool where lawful, necessary and
proportionate" [S5].

### 1.2 Lawful basis — the practical map [INF]

This section is my synthesis of how the instruments above fit together; the
individual rules are cited, the mapping is inference.

- **Private operator, ordinary CCTV analytics (intrusion detection, loitering,
  counting, PPE):** Article 6 legitimate interests is the normal basis; it
  requires a documented legitimate-interests assessment (purpose, necessity,
  balancing). DUAA 2025 adds a category of "recognised legitimate interests"
  in Schedule 4 [S16]; whether a given security use falls within it needs
  checking against the Schedule text, which I have not quoted here. [INF]
- **Private operator, anything that uniquely identifies (face match against a
  watchlist, and possibly ReID/gait — see §4):** you additionally need an
  Article 9(2) condition [S4]. Consent (9(2)(a)) is unworkable in a public
  space; the realistic route is 9(2)(g) "substantial public interest, on the
  basis of domestic law ... proportionate to the aim pursued and provide for
  suitable and specific measures" [S4], which in the UK means a DPA 2018
  Schedule 1 condition plus an appropriate policy document. [INF on which
  Schedule 1 condition fits a given deployment.]
- **Police:** DPA 2018 Part 3, not UK GDPR. *Bridges* was decided on the
  s.64 DPIA duty in Part 3 [S3].
- **Defence / national security:** outside the AI Act entirely (see §6.4) and
  subject to national-security exemptions in the DPA 2018 — but a defence
  *supplier* building a product it also sells to civil customers is back in
  scope for those civil sales. [INF]

### 1.3 DPIA triggers

UK GDPR Article 35(3) makes a DPIA mandatory in three named cases, of which
the first two are quoted verbatim: "(a) a systematic and extensive evaluation
of personal aspects relating to natural persons which is based on automated
processing, including profiling, and on which decisions are based that produce
legal effects ... or similarly significantly affect the natural person; (b)
processing on a large scale of special categories of data referred to in
Article 9(1) ..." [S6]; the third, (c), is systematic monitoring of a publicly
accessible area on a large scale [S6].

The ICO adds its own list of processing "likely to result in high risk" that
requires a DPIA [S7]. The entries that a CCTV-analytics product hits:

| ICO criterion | How a SurvSim-style product hits it |
|---|---|
| **Innovative technology** — "the use of new technologies, or the novel application of existing technologies (including AI)" | Any ML analytics |
| **Biometric data** — "Any processing of biometric data for the purpose of uniquely identifying an individual" | Face match; arguably ReID/gait |
| **Invisible processing** — the ICO defines this narrowly: personal data "not obtained direct from the data subject" where Art 14 compliance is impossible or disproportionate | *Audit correction:* CCTV captures data directly from the subject (Art 13, signage), so this criterion usually does **not** apply to own-camera analytics; it can apply to analytics on footage obtained from a third party |
| **Tracking** — monitoring geolocation or behaviour | Multi-camera tracking *is* this |
| **Data matching** | Matching across cameras or against a watchlist |
| **Large-scale profiling** | Behaviour/intent analytics across an estate |

[S7] for the criteria; the right-hand column is [INF].

**Takeaway you can say:** "Any multi-camera tracking product hits at least
two ICO DPIA criteria — innovative technology and tracking — and, at estate
scale, the statutory Art 35(3)(c) trigger (systematic monitoring of a publicly
accessible area on a large scale), before you even argue about biometrics. A
DPIA is not optional; the question is only how good it is." [INF, from S6/S7]
*(Audit 2026-09-26: an earlier version listed "invisible processing" as the
third criterion; the ICO definition does not fit own-camera CCTV — see table.)*

---

## 2. The Surveillance Camera Code — the 12 principles verbatim

Amended code laid before Parliament 16 November 2021, in force 12 January 2022 (House of Lords Library, [S18]); the gov.uk accessible version [S1] is dated 3 March 2022. Numbers matter: interviewers from UK security
backgrounds quote them by number. Verbatim from [S1]:

1. "Use of a surveillance camera system must always be for a specified purpose
   which is in pursuit of a legitimate aim and necessary to meet an identified
   pressing need."
2. "The user of a surveillance camera system must take into account its effect
   on individuals and their privacy, with regular reviews to ensure its use
   remains justified."
3. "There must be as much transparency in the use of a surveillance camera
   system as possible, including a published contact point for access to
   information and complaints."
4. "There must be clear responsibility and accountability for all surveillance
   camera system activities including images and information collected, held
   and used."
5. "Clear rules, policies and procedures must be in place before a
   surveillance camera system is used, and these must be communicated to all
   who need to comply with them."
6. "No more images and information should be stored than that which is
   strictly required for the stated purpose of a surveillance camera system,
   and such images and information should be deleted once their purposes have
   been discharged."
7. "Access to retained images and information should be restricted and there
   must be clearly defined rules on who can gain access and for what purpose
   such access is granted; the disclosure of images and information should
   only take place when it is necessary for such a purpose or for law
   enforcement purposes."
8. "Surveillance camera system operators should consider any approved
   operational, technical and competency standards relevant to a system and
   its purpose and work to meet and maintain those standards."
9. "Surveillance camera system images and information should be subject to
   appropriate security measures to safeguard against unauthorised access and
   use."
10. "There should be effective review and audit mechanisms to ensure legal
    requirements, policies and standards are complied with in practice, and
    regular reports should be published."
11. "When the use of a surveillance camera system is in pursuit of a legitimate
    aim, and there is a pressing need for its use, it should then be used in
    the most effective way to support public safety and law enforcement with
    the aim of processing images and information of evidential value."
12. "Any information used to support a surveillance camera system which
    compares against a reference database for matching purposes should be
    accurate and kept up to date."

**Engineer's mapping of the principles to product features [INF]:**

| Principle | Product feature that evidences it |
|---|---|
| 1 purpose | Per-camera, per-rule purpose field in configuration; rules cannot be enabled without one |
| 2 review | Scheduled re-justification reminders; usage statistics per rule |
| 4 accountability | Named owner per camera group; immutable audit log |
| 6 minimisation | Retention per purpose; metadata-only storage by default; auto-deletion |
| 7 access | Role-based access; export logged with reason code |
| 8 standards | i-LIDS-style operational testing — SurvSim's evaluation is exactly this (docs/research 00 fact 2) |
| 9 security | Encryption at rest, signed firmware, network segmentation |
| 10 audit | Exportable compliance report |
| 11 effectiveness | Evidential-grade export: timestamps, hash chain, calibration |
| 12 accuracy of reference DB | Watchlist expiry, provenance per entry |

Principle 11 is the one engineers forget: the Code treats *effectiveness* as a
privacy principle. A system that intrudes and does not work fails
proportionality. That is the strongest ethical argument for SurvSim's whole
evaluation-first approach — measuring false alarms per camera-hour and i-LIDS
timing is not just product quality, it is the evidence that the intrusion buys
something. [INF]

---

## 3. *R (Bridges) v Chief Constable of South Wales Police* [2020] EWCA Civ 1058

Handed down 11 August 2020; Sir Terence Etherton MR, Dame Victoria Sharp PQBD,
Singh LJ; on appeal from [2019] EWHC 2341 (Admin); unanimous [S3].

### 3.1 Facts (from the court's press summary [S3])

- System: **AFR Locate** — extracts faces from a live feed, compares to a
  watchlist; no match ⇒ facial image automatically deleted; match ⇒ alert,
  human officer reviews before any intervention.
- About 50 deployments between May 2017 and April 2019; overt, not secret.
- Watchlists of 400–800 people; maximum capacity 2,000 images.
- "AFR Locate is capable of scanning 50 faces per second"; around 500,000
  faces estimated scanned over the 2017–2018 deployments.
- Mr Bridges was near two deployments (Queen Street, Cardiff, 21 Dec 2017;
  the defence exhibition at Motorpoint Arena, 27 Mar 2018). He was not on a
  watchlist; SWP did not contest that his image was captured and near-
  instantly deleted.
- The Divisional Court (4 Sept 2019) dismissed on all grounds.

### 3.2 The five grounds and the outcome (all from [S3])

| # | Ground | Result | Court's reasoning |
|---|---|---|---|
| 1 | Interference not "in accordance with the law" (Art 8(2)) | **Succeeded** | Framework (DPA 2018 + Surveillance Camera Code + local policies) gave "no clear guidance on where AFR Locate could be used and who could be put on a watchlist". "This was too broad a discretion to afford to the police officers." |
| 2 | Not proportionate (Art 8(2)) | **Failed** | Benefits "potentially great", impact on Mr Bridges "minor"; weighing exercise correctly done. |
| 3 | DPIA inadequate (DPA 2018 s.64) | **Succeeded** | DPIA was written on the basis that Art 8 was not infringed, so it was deficient. |
| 4 | No "appropriate policy document" (s.42) | **Failed** | Did not need deciding; the two deployments pre-dated DPA 2018. |
| 5 | PSED breached (Equality Act s.149) | **Succeeded** | SWP did not take reasonable steps to enquire whether the software had bias on racial or sex grounds. The Court noted there was no clear evidence that the software *was* biased. |

### 3.3 What an engineer should take from it [INF]

1. **Proportionality was not the problem.** The court accepted the trade-off.
   What failed was *governance*: who/where discretion, the DPIA, and the bias
   enquiry. That is good news for a product company, because governance is
   something a product can be designed to support.
2. **"Who and where" is a configuration problem.** A product that forces an
   explicit, logged watchlist-inclusion criterion and an explicit deployment
   location policy directly addresses Ground 1.
3. **A DPIA that assumes the answer is worthless.** Ground 3 — the DPIA started
   from "Art 8 is not engaged", so it never assessed the interference.
4. **You must go and look for bias, even if you don't find any.** Ground 5 is
   an obligation of *enquiry*, not of result. For a supplier, this means
   shipping per-demographic performance evidence. Synthetic data with
   controlled demographics is a legitimate tool here — SurvSim's population
   generator can set demographics explicitly, which a real dataset cannot —
   but only if the synthetic-to-real gap is characterised, otherwise the
   evidence proves nothing about the deployed system.
5. **Deletion of non-matches did not save it.** Instant deletion was part of
   the facts; the interference was still found to engage Art 8 and the
   deployment still failed on law and governance.

Note Ground 1's framework explicitly included the Surveillance Camera Code as
part of the legal basis [S3]. The Code alone was not specific enough.

---

## 4. Biometric data: does appearance ReID or gait count?

### 4.1 The definitions (verbatim)

- **DPA 2018 s.205:** "personal data resulting from specific technical
  processing relating to the physical, physiological or behavioural
  characteristics of an individual, which allows or confirms the unique
  identification of that individual, such as facial images or dactyloscopic
  data" [S2].
- **UK GDPR Art 9(1)** restricts "biometric data *for the purpose of uniquely
  identifying* a natural person" [S4] (emphasis added).
- **EU AI Act Art 3(34):** "'biometric data' means personal data resulting from
  specific technical processing relating to the physical, physiological or
  behavioural characteristics of a natural person, such as facial images or
  dactyloscopic data" [S9]. Note: *no* "allows or confirms unique
  identification" limb — the AI Act's definition is broader than GDPR's.
- **AI Act Art 3(35) biometric identification:** "the automated recognition of
  physical, physiological, behavioural, or psychological human features for
  the purpose of establishing the identity of a natural person by comparing
  biometric data of that individual to biometric data of individuals stored in
  a database" [S9].
- **AI Act Art 3(40) biometric categorisation system:** assigning people "to
  specific categories on the basis of their biometric data, unless it is
  ancillary to another commercial service and strictly necessary for objective
  technical reasons" [S9].

### 4.2 The EDPB position (Guidelines 3/2019 on video devices, v2.0 adopted 29 January 2020) [S8]

Paragraph 74: "The video footage of an individual cannot however in itself be
considered as biometric data under Article 9, if it has not been specifically
technically processed in order to contribute to the identification of an
individual."

Paragraph 75: for Article 9 to apply, it "requires that biometric data is
processed 'for the purpose of uniquely identifying a natural person'."

Example 4 (after para 80 — *audit correction: not para 76*), verbatim in substance: a shop owner customising
advertising by gender and age; "If that system does not generate biometric
templates in order to uniquely identify persons but instead just detects those
physical characteristics in order to classify the person then the processing
would not fall under Article 9". The general rule stated: "when the purpose of
the processing is for example to distinguish one category of people from
another but not to uniquely identify anyone the processing does not fall under
Article 9."

The EDPB also warns that **temporary templates count**: where a system
generates templates of passers-by to check whether they are enrolled, the
guidelines say these "temporary templates constitute biometric data" even if
deleted within the shortest possible period [S8, §5.1, Example 5 — a shop-owner
facial-recognition advertising system].

### 4.3 The ICO position [S10][S7]

The ICO's biometric-recognition guidance restates the test — data that
"allow[s] or confirm[s] someone's unique identification" through "specific
technical processing" of physical, physiological or behavioural
characteristics — and lists behavioural characteristics as within scope [S10].
The fetched page **does not specifically address gait or appearance-based
re-identification** [S10]; I could not find a published ICO statement on
whether a clothing-appearance ReID embedding is biometric. The ICO's DPIA list
names "Any processing of biometric data for the purpose of uniquely
identifying an individual" as high-risk [S7].

### 4.4 Applying it: a classification table [INF throughout]

| Feature | Technical processing? | Unique identification purpose? | Likely status |
|---|---|---|---|
| Person detection, counting, occupancy | Yes | No | Personal data (if images retained), **not** Art 9 — EDPB para 80 logic |
| Loiter / intrusion / line-cross | Yes | No — rule on location/time | Not Art 9 |
| Age/gender estimation for statistics | Yes | No — categorisation | Not Art 9 under GDPR (EDPB Ex. 4), **but** AI Act "biometric categorisation" if it infers sensitive attributes → Annex III 1(b) high-risk; and **prohibited** under Art 5(1)(g) if it infers race, political opinions, trade-union membership, religious/philosophical beliefs, sex life or sexual orientation [S9] (age/gender are not in that list) |
| Single-camera tracker (IoU / Kalman) | Weakly | Keeps a track ID within one view; no template | Probably not Art 9 |
| **Appearance ReID across cameras** | Yes — an embedding of body/clothing | Its whole purpose is to establish that two sightings are the *same individual* | **Contestable.** Argument *for* Art 9: the embedding is a template that "allows or confirms unique identification" within the estate. Argument *against*: clothing is not a "physical, physiological or behavioural characteristic" of the person, it changes daily, and the system singles out but does not link to a real-world identity. |
| **Gait recognition** | Yes | Yes if matched across time | Gait is a textbook behavioural characteristic; a gait template used to match is squarely within the s.205 definition. Treat as biometric. |
| Face recognition against a watchlist | Yes | Yes | Biometric, Art 9, and (EU) remote biometric identification |

**The key engineering point:** "singling out" can be identification. Recital
26 GDPR-style reasoning (not fetched here, so flagged [INF]) treats being able
to single a person out as making data personal; a design that reduces ReID to
*session-scoped, non-persistent, estate-local* matching with no link to a name
and short template lifetime is the defensible position — but the EDPB's
"temporary templates constitute biometric data" line [S8] means short lifetime
alone does not take you out of scope. The honest answer in an interview:
"ReID is a grey zone; I would design and document as if it were biometric,
because the cost of being wrong is a *Bridges*-style finding, and the cost of
over-complying is a DPIA I should be doing anyway."

**SurvSim relevance:** SurvSim's disguise/appearance-epoch work (the
clothes-changing ReID niche, docs/research 00 fact 6) is research into making
cross-camera identification *robust to clothing changes* — i.e. moving from
clothing-appearance towards body-shape and gait. That moves the product
*towards* unambiguous biometric processing. Say this out loud if asked; it
shows you see the second-order consequence. [INF]

---

## 5. Retention and anonymisation

### 5.1 Retention

- **Code principle 6:** store no more than "strictly required for the stated
  purpose" and delete "once their purposes have been discharged" [S1].
- **EDPB 3/2019 §8:** footage "should in most cases (e.g. for the purpose of
  detecting vandalism) be erased, ideally automatically, after a few days. The
  longer the storage period set (especially when beyond 72 hours), the more
  argumentation for the legitimacy of the purpose and the necessity of storage
  has to be provided" [S8]. **72 hours is a justification threshold, not a
  legal limit** — a common misquote.
- UK practice commonly uses ~31 days; I did not find a primary source setting
  that figure and it should not be quoted as a rule. [INF]

### 5.2 Designing retention into an analytics product [INF]

- **Split the stores.** Raw video (short, purpose-bound), event clips (longer,
  tied to an alarm/incident), metadata (tracks, boxes — often retained longest
  and forgotten), and embeddings/templates (the most sensitive; shortest
  lifetime; never exported by default).
- **Embeddings are the trap.** A deployment that deletes video at 72 hours but
  keeps ReID embeddings for 30 days has kept the most identifying artefact
  longest.
- **Legal hold** must suspend deletion per incident, logged.
- **Deletion must be verifiable** — a scheduled job whose output is a signed
  record, in the same way SurvSim's CLAUDE.md insists that editor scripts
  "write a result file" because stdout proves nothing.

### 5.3 Anonymisation vs pseudonymisation [INF]

- Face/body blurring at export is **redaction**, not anonymisation, if the
  controller keeps the original.
- Track IDs are **pseudonymous** identifiers; they remain personal data while
  re-linkable to footage.
- True anonymisation for training data means the individual cannot be
  re-identified by any means reasonably likely to be used — hard to achieve
  with video, which is one of the strongest *legal* arguments for synthetic
  training data. (Which is where §8 bites.)

---

## 6. EU AI Act (Regulation (EU) 2024/1689) and the Digital Omnibus (2026/1744)

### 6.1 Relevance to a UK company [INF]

The AI Act applies to providers placing systems on the EU market or whose
output is used in the EU, regardless of establishment (territorial provisions
not quoted here). A UK surveillance-analytics firm selling into any EU state
is in scope. The UK has no equivalent statute.

### 6.2 Prohibitions relevant to surveillance (Art 5) [S9]

- **5(1)(d)** — AI to "assess or predict the risk of a natural person
  committing a criminal offence, based solely on the profiling of a natural
  person or on assessing their personality traits and characteristics", with a
  carve-out for supporting human assessment "already based on objective and
  verifiable facts directly linked to a criminal activity".
- **5(1)(e)** — systems "that create or expand facial recognition databases
  through the untargeted scraping of facial images from the internet or CCTV
  footage". **Note "or CCTV footage"** — directly relevant to anyone building a
  face gallery from surveillance video.
- **5(1)(f)** — inferring emotions "in the areas of workplace and education
  institutions, except ... for medical or safety reasons".
- **5(1)(h)** — "the use of 'real-time' remote biometric identification systems
  in publicly accessible spaces for the purposes of law enforcement, unless and
  in so far as such use is strictly necessary for" (i) targeted search for
  victims of abduction, trafficking, sexual exploitation, or missing persons;
  (ii) prevention of a "specific, substantial and imminent threat" to life or a
  terrorist threat; (iii) localisation/identification of a suspect of
  specified serious offences.

Definitions that make these bite [S9]:

- **Art 3(41) remote biometric identification system:** "identifying natural
  persons, without their active involvement, typically at a distance through
  the comparison of a person's biometric data with the biometric data contained
  in a reference database".
- **Art 3(42) real-time:** capture, comparison and identification "all occur
  without a significant delay, comprising not only instant identification, but
  also limited short delays in order to avoid circumvention".
- **Art 3(44) publicly accessible space:** "any publicly or privately owned
  physical place accessible to an undetermined number of natural persons" —
  so a shopping centre or station concourse counts.

**Behaviour analytics and 5(1)(d) [INF]:** a "suspicious behaviour" score is
not profiling on personality traits — it is based on observed conduct in a
place — but a product that *predicted offending by a person* from their
attributes would be. SurvSim's catalogue is conduct-based (loiter, tamper,
fence-approach), which is the defensible side. Keep it that way; do not ship
"risk score per person" language.

### 6.3 Annex III high-risk — point 1, Biometrics (verbatim) [S9]

"Biometrics, in so far as their use is permitted under relevant Union or
national law:
(a) remote biometric identification systems. This shall not include AI systems
intended to be used for biometric verification the sole purpose of which is to
confirm that a specific natural person is the person he or she claims to be;
(b) AI systems intended to be used for biometric categorisation, according to
sensitive or protected attributes or characteristics based on the inference of
those attributes or characteristics;
(c) AI systems intended to be used for emotion recognition."

(Annex III also covers critical infrastructure (point 2), law enforcement
(point 6) and migration/border (point 7); point 2 is quoted in [S9] as "safety
components in the management and operation of critical digital infrastructure,
road traffic, or in the supply of water, gas, heating or electricity".)

**Classification of a typical intrusion-detection product [INF]:** perimeter
intrusion detection with no identification is *not* in Annex III point 1. It
becomes high-risk if it adds (a) post-remote face search, (b) sensitive-
attribute categorisation, or (c) "intent/aggression" labels derived from
biometric data — note Art 3(39) defines an emotion recognition system as
inferring "emotions or intentions" from biometric data [S9]. An "intent"
classifier built on pose/gait is uncomfortably close to that wording.

### 6.4 Exclusions [S9]

- **Art 2(3):** the Regulation "does not apply to AI systems where and in so far
  they are placed on the market, put into service, or used with or without
  modification exclusively for military, defence or national security
  purposes". The word **"exclusively"** is load-bearing: a dual-use product
  sold to both a MoD and a shopping centre is in scope for the shopping centre.
- **Art 2(6):** does not apply to systems "specifically developed and put into
  service for the sole purpose of scientific research and development".
- **Art 2(8):** does not apply to "research, testing or development activity
  ... prior to their being placed on the market", but "Testing in real world
  conditions shall not be covered by that exclusion".

**For SurvSim [INF]:** simulator-based development and evaluation sits
squarely in Art 2(8) pre-market R&D. A field trial on a live site does not.

### 6.5 Dates — original and as amended by 2026/1744

**Original Art 113 (verbatim) [S9]:** "It shall apply from 2 August 2026.
However: (a) Chapters I and II shall apply from 2 February 2025; (b) Chapter
III Section 4, Chapter V, Chapter VII and Chapter XII and Article 78 shall
apply from 2 August 2025, with the exception of Article 101; (c) Article 6(1)
and the corresponding obligations in this Regulation shall apply from 2 August
2027."

So the **Article 5 prohibitions (Chapter II) have applied since 2 February
2025** — they were never deferred.

**The 2026/1744 reference is verified.** Regulation (EU) 2026/1744 of the
European Parliament and of the Council of 8 July 2026 "amending Regulations
(EU) 2024/1689, (EU) 2018/1139 and (EU) 2023/1230 as regards the
simplification of the implementation of harmonised rules on artificial
intelligence (Digital Omnibus on AI)" [S11]. Per the EUR-Lex text: published
in the Official Journal 24 July 2026 and entering into force "on the third
day following that of its publication" [S11]; and "the date of application of
Sections 1, 2 and 3 of Chapter III is set to **2 December 2027** for AI
systems classified as high-risk pursuant to Article 6(2) and Annex III" [S11]
(was 2 August 2026).

**Audit 2026-09-26 — now verified against the Regulation text [S11]** (these
were previously secondary-only):

* Entry into force: third day after 24 July 2026 OJ publication, i.e.
  **27 July 2026** (Art 4 of 2026/1744). Amended Art 113 adds point (d):
  "Articles 102 to 110 shall apply from 27 July 2026."
* Amended Art 113(c): Chapter III Sections 1–3 apply "(i) 2 December 2027 as
  regards AI systems classified as high-risk pursuant to Article 6(2) and
  Annex III; and (ii) **2 August 2028** as regards ... Article 6(1) and
  Annex I" — confirmed.
* National AI regulatory sandbox "operational by **2 August 2027**" (amended
  Art 57(1)) — confirmed.
* Transparency: the general 2 August 2026 date for Art 50 is unchanged, **but**
  providers of generative systems placed on the market before 2 August 2026
  have until **2 December 2026** to comply with Art 50(2) (marking). The
  earlier "did not move" is therefore only half right.
* **New prohibitions** (not in the earlier version): Art 5(1)(ba)/(bb) ban AI
  systems generating non-consensual intimate imagery of identifiable persons
  and CSAM; they apply from **2 December 2026** (amended Art 113(a)). The
  original Art 5 prohibitions still date from 2 February 2025.
* Legislative history from the recitals/footnotes: EP position 16 June 2026;
  signed Strasbourg 8 July 2026.

**One-liner to recite:** "Prohibitions since February 2025, GPAI since August
2025, Annex III high-risk now December 2027 after the July 2026 Digital
Omnibus, 2026/1744."

---

## 7. Defence dual-use and UK export control

### 7.1 The list

The UK Strategic Export Control Lists ("the consolidated list") were last
updated **16 December 2025** (UK Export Control List 2025, 398 pp.) [S14];
updates occur "about twice a year" and "It is your responsibility to ensure
that you are aware of all recent updates" [S14]. The consolidated list
compiles seven lists including the UK Military List, UK Dual-Use Control List (Schedule 3 of the
Export Control Order 2008) and the Dual-Use List (Annexes I and IV of assimilated
Council Regulation (EC) No. 428/2009), both last amended by SI 2025/1197, Human Rights List, and UK Security and Human Rights List [S15].
The online checker is at ecochecker.trade.gov.uk [S14].

### 7.2 Entries a surveillance-analytics company must read [S15]

- **ML5.b** — "Other fire control, surveillance and warning equipment, and
  related systems ... specially designed for military use": "1. Target
  acquisition, designation, range-finding, surveillance or tracking systems;
  2. Detection, recognition or identification equipment; 3. Data fusion or
  sensor integration equipment".
- **ML21.a** — "Software" specially designed or modified for the development,
  production, operation or maintenance of equipment on the Military List.
- **ML21.b.1–2** — "'Software' that is both specially designed for military use
  and specially designed for modelling, simulating or evaluating military
  weapons systems"; and "... for modelling or simulating military operational
  scenarios".
- **ML21.b.4** — software specially designed for military use and for C3I/C4I.
- **6A003** (dual-use cameras) — imaging cameras, controlled only above
  specified performance parameters. *Audit correction:* the 6A003.b note
  carves out only television or video cameras "specially designed for
  television broadcasting" — not ordinary video cameras generally; ordinary
  CCTV cameras escape because they fall below the parameters, not because of
  the note.

### 7.3 Where SurvSim sits [INF]

- As a *civil* surveillance simulator, SurvSim is not "specially designed for
  military use" and so falls outside ML21.b. The day it is adapted to model
  "military operational scenarios" (e.g. a base-perimeter scenario pack built
  to a MoD requirement), ML21.b.2 becomes a live question. **"Specially
  designed" is the hinge** — and it is a fact question about the design
  history, which is why design documents should record civil purpose.
- A tracking/fusion product built to a defence customer's requirement could
  hit ML5.b.1–3 ("surveillance or tracking systems", "detection, recognition or
  identification equipment", "data fusion or sensor integration") and ML21.a
  for its software.
- **Technology controls have public-domain and basic-research carve-outs:**
  "Controls on 'technology' transfer do not apply to information 'in the public
  domain' or to 'basic scientific research'" [S15]; "in the public domain"
  means made available "without restrictions upon its further dissemination
  (copyright restrictions do not remove 'technology' or 'software' from being
  'in the public domain')" [S15]. Publishing a paper is protected; handing a
  foreign partner an unpublished ML5-adjacent model is not.
- Intangible transfer counts: emailing weights or pushing to a repo readable
  abroad can be an export. [INF — the list defines what is controlled; the
  transfer rules are in the Export Control Order, not fetched here.]
- **Practical rule:** classify early with ECJU (the checker, then a Control
  List Classification request) before a first overseas demo, not after.

---

## 8. Ethics and licensing of synthetic humans — the MetaHuman problem

### 8.1 What Epic's licence says

From Epic's licensing page for MetaHuman (fetched 2026-09-26) [S13]. *Audit
note: `metahuman.com/en-US/license` now redirects automated fetches to an Epic
login; `https://www.metahuman.com/license` (no locale) serves the same FAQ in
its HTML/JSON-LD and the AI clause below was re-confirmed verbatim from it on
2026-09-26.*

- MetaHuman "is included as part of your standard Unreal Engine license,
  meaning it's free to use for anyone making under $1 million USD in revenue
  and Unreal Engine standard terms apply above that threshold. MetaHumans can
  be used with any engine or creative software."
- **The AI clause, verbatim from the FAQ:** "You can use MetaHuman characters
  and animation in workflows that incorporate artificial intelligence
  technology. However, you may not use MetaHuman characters or animation curves
  to build or enhance any database or train or test artificial intelligence,
  machine learning, deep learning, neural networks, or similar technologies (as
  further detailed in the Unreal Engine EULA). This includes the use of
  rendered output from MetaHuman digital characters and animation curves, if
  created to replicate the functionality of MetaHuman."
- "If you require custom legal terms or dedicated Epic support ... Contact
  us" [S13].

A secondary report of the June 2025 licence change says the same: use in AI
workflows is allowed, "but not to train or enhance the AI models themselves"
[S17].

I could not fetch the Unreal Engine EULA body itself (HTTP 403 to automated
fetch, and the page is script-rendered) so the exact EULA section number is
**unverified**.

### 8.2 What it means for SurvSim [INF]

- Read plainly, "train or test artificial intelligence ... neural networks"
  covers rendering MetaHumans to produce a detection/ReID training set, and
  covers *evaluating* a detector on MetaHuman renders ("test").
- The last sentence ("rendered output ... if created to replicate the
  functionality of MetaHuman") is ambiguous: one reading limits the
  rendered-output restriction to training a MetaHuman *competitor*; the other
  reads it as an extension, not a limitation. The first sentence's "characters
  ... to ... train or test" does not depend on that reading.
- SurvSim's current route to wardrobe and body variation (CLAUDE.md: MetaHuman
  parametric body, DNA rigging, the UE 5.8 editor route) is therefore
  **licence-blocked for its core purpose** absent a custom licence.
- **Options, in order of preference:**
  1. Ask Epic for custom terms (the FAQ invites it [S13]) — do this before
     investing more engineering in the MetaHuman route.
  2. Use body models whose licence permits ML training — or assets
     commissioned/owned outright; check each licence's ML clause before use.
  3. Keep MetaHuman strictly for non-ML uses (visualisation, demos) and label
     any dataset provenance so no MetaHuman render reaches a training or test
     split.
- **Dataset provenance should be a GT field.** Every rendered frame should
  record which asset licences it depends on, so a licence finding can be
  enforced by a filter rather than a re-render. SurvSim already writes
  `identities.parquet`; an `asset_licence` column there is the natural place.

**This is the talking point for "tell me about a risk you found".** It is also
consistent with the MOT20 licence realisation already in the repo's history:
data licences are part of the engineering, not paperwork after it.

### 8.3 Likeness and consent ethics [INF]

- Synthetic humans avoid collecting real people's images, which is the main
  privacy argument for them — **provided** the assets are not scans of real
  people without consent. Mesh-to-MetaHuman from a real scan re-introduces a
  real person's likeness; that person's consent and the scan licence then
  govern.
- Demographic control is an ethical benefit (Bridges Ground 5: you must
  enquire into bias [S3]) *and* a risk: generating "suspicious" behaviour
  disproportionately on one synthetic demographic bakes bias in. SurvSim's
  behaviour assignment should be demographic-independent by construction and
  tested for it.
- Hard negatives (CLAUDE.md principle 3) are also an ethical tool: a system
  trained without innocent look-alikes over-alarms on ordinary people.

---

## 9. Likely interview questions and crisp answers

**Q: Is a person-ReID embedding biometric data under UK GDPR?**
A: The test is specific technical processing of physical, physiological or
behavioural characteristics that allows or confirms unique identification,
and Art 9 bites where the *purpose* is unique identification [S2][S4]. A
cross-camera ReID embedding is technical processing whose purpose is to decide
two sightings are the same person, so there's a real argument it is. The EDPB
says raw footage isn't biometric until specifically processed for
identification [S8] and that even temporary templates count [S8]. I'd treat it
as biometric: DPIA, Art 9 condition, short template life, estate-local, no
link to names.

**Q: What did Bridges actually decide?**
A: Three of five grounds succeeded: not in accordance with law because of
too-broad who/where discretion; DPIA deficient because it assumed Art 8 wasn't
engaged; PSED breached because SWP never enquired into bias. Proportionality
*failed* as a ground — the court accepted the trade-off [S3].

**Q: Does the EU AI Act ban real-time face recognition?**
A: For law enforcement in publicly accessible spaces, yes, except three
narrowly defined objectives, since 2 February 2025 [S9]. For private operators
it's not an Art 5 prohibition; RBI is Annex III high-risk, with obligations now
applying from 2 December 2027 under 2026/1744 [S11].

**Q: Does the AI Act apply to defence customers?**
A: Not where the system is used *exclusively* for military, defence or
national security [S9]. Sell the same product to a civil customer and it's in
scope for that sale. [INF]

**Q: How long should you keep footage?**
A: As short as the purpose needs; the EDPB treats beyond 72 hours as needing
more justification, not as a limit [S8]. And embeddings are the thing people
forget to expire. [INF]

**Q: Could you train your detector on MetaHuman renders?**
A: Not under the standard terms as I read them — Epic's FAQ says MetaHuman
characters may not be used to "train or test" AI [S13]. I'd seek custom terms
or use assets licensed for ML, and record asset licences per frame. [INF on
the reading]

**Q: Is your simulator export-controlled?**
A: As a civil tool, I don't believe so; ML21.b.2 catches software "specially
designed for military use and ... for modelling or simulating military
operational scenarios" [S15]. The day we build a defence scenario pack to a
military requirement, we classify it with ECJU first. [INF]

---

## 10. The decision checklist (recite this)

**Before building a feature**
1. **Purpose.** What pressing need, what legitimate aim? Written down per
   camera/rule. (Code P1 [S1])
2. **Identify?** Does the feature *uniquely identify* — face match, gait,
   persistent ReID template? If yes → biometric, Art 9 condition, DPIA
   mandatory. If only detects/counts/categorises → not Art 9, but check AI Act
   categorisation. ([S2][S4][S8])
3. **EU market?** Map against AI Act Art 5 prohibitions (in force since Feb
   2025) and Annex III point 1 (high-risk from 2 Dec 2027). Emotion or
   "intention" from biometrics → emotion-recognition definition. ([S9][S11])
4. **Defence?** "Exclusively" military ⇒ outside AI Act; any civil sale ⇒
   inside. Check ML5/ML21 and ECJU before any foreign transfer. ([S9][S15])

**Before deploying**
5. **DPIA** — hits innovative tech, tracking, invisible processing at minimum;
   must *assess* the interference, not assume it away (Bridges G3). ([S7][S3])
6. **Who and where** — explicit, logged criteria for watchlist inclusion and
   deployment locations (Bridges G1). ([S3])
7. **Bias enquiry** — per-demographic performance evidence, documented, even
   if the result is "no bias found" (Bridges G5). ([S3])
8. **Lawful basis** — legitimate-interests assessment; Art 9(2)(g) + DPA 2018
   Sch 1 if biometric; Part 3 if police. ([S4])

**Running it**
9. **Retention** — per store (video, clips, metadata, embeddings); beyond
   72 h needs argument; automatic, verifiable deletion. ([S8][S1] P6)
10. **Access and audit** — role-based, export logged with reason, published
    review. (Code P7, P9, P10 [S1])
11. **Effectiveness** — measure it operationally (false alarms per camera-hour,
    late alarm = false alarm); an ineffective intrusion fails proportionality.
    (Code P11 [S1]) [INF on the link]

**For the data behind the model**
12. **Licences** — every asset and dataset's ML-training clause checked;
    MetaHuman standard terms forbid train/test ([S13]); licence recorded per
    frame.
13. **Likeness** — no scans of real people without consent; behaviour labels
    independent of synthetic demographics. [INF]

Short form: **Purpose — Identify? — EU? — Defence? — DPIA — Who/Where — Bias —
Basis — Retain — Access — Effective — Licence — Likeness.**

---

## Sources (all fetched 2026-09-26)

| Tag | Source | URL |
|---|---|---|
| S1 | Home Office, Amended Surveillance Camera Code of Practice (accessible version), Nov 2021 | https://www.gov.uk/government/publications/update-to-surveillance-camera-code/amended-surveillance-camera-code-of-practice-accessible-version |
| S2 | Data Protection Act 2018 s.205 | https://www.legislation.gov.uk/ukpga/2018/12/section/205 |
| S3 | Court of Appeal press summary, *R (Bridges) v CC South Wales Police* [2020] EWCA Civ 1058, 11 Aug 2020 (and judgment landing page https://www.judiciary.uk/judgments/r-bridges-v-cc-south-wales/) | https://www.judiciary.uk/wp-content/uploads/2020/08/R-Bridges-v-CC-South-Wales-ors-Press-Summary.pdf |
| S4 | UK GDPR Article 9 | https://www.legislation.gov.uk/eur/2016/679/article/9 |
| S5 | ICO, Guidance on video surveillance (including CCTV) | https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/cctv-and-video-surveillance/guidance-on-video-surveillance-including-cctv/ |
| S6 | UK GDPR Article 35 | https://www.legislation.gov.uk/eur/2016/679/article/35 |
| S7 | ICO, Examples of processing likely to result in high risk (DPIA) | https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/accountability-and-governance/data-protection-impact-assessments-dpias/examples-of-processing-likely-to-result-in-high-risk/ |
| S8 | EDPB Guidelines 3/2019 on processing of personal data through video devices, v2.0 adopted 29 Jan 2020 (paras 74–76, Example 4, §5.1, §8) | https://www.edpb.europa.eu/sites/default/files/files/file1/edpb_guidelines_201903_video_devices_en_0.pdf |
| S9 | Regulation (EU) 2024/1689 (AI Act), OJ L 12.7.2024 — Arts 2, 3, 5, 113, Annex III (text via EU Publications Office Cellar; ELI https://eur-lex.europa.eu/eli/reg/2024/1689/oj/eng) | https://publications.europa.eu/resource/cellar/dc8116a1-3fe6-11ef-865a-01aa75ed71a1.0006.03/DOC_1 |
| S10 | ICO, Biometric data guidance: biometric recognition | https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/lawful-basis/biometric-data-guidance-biometric-recognition/ |
| S11 | Regulation (EU) 2026/1744 (Digital Omnibus on AI), 8 Jul 2026 | https://eur-lex.europa.eu/eli/reg/2026/1744/oj/eng |
| S12 | Secondary (not primary): Gibson Dunn / euaiactchecklist summaries of 2026/1744 via web search | https://www.gibsondunn.com/eu-ai-act-omnibus-agreement-postponed-high-risk-deadlines-and-other-key-changes/ ; https://euaiactchecklist.com/eu-ai-act-digital-omnibus-2026-1744.html |
| S13 | Epic Games, Licensing MetaHuman (page + FAQ) | https://www.metahuman.com/en-US/license |
| S14 | GOV.UK, Consolidated list of strategic military and dual-use items that require export authorisation (updated 16 Dec 2025) | https://www.gov.uk/government/publications/uk-strategic-export-control-lists-the-consolidated-list-of-strategic-military-and-dual-use-items-that-require-export-authorisation |
| S15 | UK Strategic Export Control Lists 2025 (PDF) — ML5, ML21, 6A003, definitions, GTN | https://assets.publishing.service.gov.uk/media/69415ba1f065108822537524/uk_export_control_list_2025.pdf |
| S16 | Data (Use and Access) Act 2025 (c. 18), contents | https://www.legislation.gov.uk/ukpga/2025/18/contents |
| S18 | House of Lords Library, "Surveillance Camera Code of Practice: regret motion" (laid 16 Nov 2021, in force 12 Jan 2022) | https://lordslibrary.parliament.uk/surveillance-camera-code-of-practice-regret-motion/ |
| S17 | Secondary: CG Channel, "You can now sell MetaHumans, or use them in Unity or Godot", 4 Jun 2025 | https://www.cgchannel.com/2025/06/you-can-now-sell-metahumans-or-use-them-in-unity-or-godot/ |

**Not fetched / unverified:** Unreal Engine EULA body (403); full *Bridges*
judgment text (BAILII 403 — press summary used instead); GDPR Recital 26; the
Export Control Order 2008 transfer provisions; DUAA 2025 Schedule 4 text;
~~secondary claims about non-Annex-III dates in 2026/1744~~ (verified
2026-09-26 against [S11]; [S12] no longer needed for them).
