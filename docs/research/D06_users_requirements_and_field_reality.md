# D06 · The Users: Who Actually Operates Surveillance Analytics, What They Want, How They Work, What Breaks

**Scope.** This dossier is about *people*, not algorithms. Its subject is the
seven user communities who sit downstream of every claim a video-analytics vendor
makes — public-space CCTV operators, CNI security managers, border agencies,
police, defence ISR users, event and stadium security, and (lightly) retail and
corporate GSOCs. For each: who they are, what doctrine and guidance governs them,
what they write into tenders, what their own post-implementation reviews and
public inquiries concluded, what the academic ethnographers found when they sat
in the room, and what they consequently ask of an AI vendor — and of a simulator.

**Why this document exists.** R01–R05 in this directory establish what the
technology can do and how it is measured. None of them answers the question a
customer actually asks in the first ten minutes of a meeting, which is never
"what is your frame-level AUC" and is always some version of *"who else uses
this, what does it do to my control room, and what happens when it is wrong?"*
A person who can answer that question in the customer's own vocabulary — naming
their guidance documents, their staffing constraints, their inquiry findings and
their procurement gates — is a different kind of interlocutor from someone who
can only talk about models. That is the capability this document is trying to
transfer.

**Deliberate non-duplication.** Two neighbouring sections already cover adjacent
ground and are **not** repeated here:

- [`R03 §5` *Human factors: the actual bottleneck*](./R03_behaviour_intent_anomaly_detection.md)
  — the vigilance-decrement literature (Applied Ergonomics 2012/2014, the PLOS ONE
  inattentional-blindness study), alarm-fatigue arithmetic, the false-alarm-filtering
  market (Calipsa, Ambient.ai, Hakimo), control-room alert design and operator
  explainability. **Read that first.** This document treats those findings as
  given and asks instead *who the person experiencing them is, how they are
  employed, and what they will write into a specification because of it.*
- [`R05 Part A §1`](./R05_multisensor_fusion_and_nl_retrieval.md) — the
  detect→assess→delay→respond doctrine, NPSA/CSE/CAPSS as procurement gates,
  i-LIDS as an assurance scheme, the US Integrated Surveillance Tower lineage,
  EUROSUR as a legal object, the sensor menu and the nuisance-alarm-rate problem.
  This document picks those up at the *organisational* level: the tender, the
  post-implementation review, the inquiry, the union grievance.

---

## 0. Sourcing note — read this before quoting anything onward

**This session hit a hard research-tooling wall and the reader must know its
shape before trusting any sentence below.**

1. **The web-search budget was exhausted session-wide after nine queries of the
   thirty-five-plus planned.** The tool returned: *"Web search was not performed:
   this session has used its web search budget (200 of 200 WebSearch calls)…
   If more searches are genuinely needed, ask the user to raise
   `CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION`."* The 200-call budget is shared
   across the session, and earlier dossiers in this directory consumed it.
2. **Direct page fetching is also blocked.** Every attempted fetch returned
   `EGRESS_BLOCKED` from the network proxy, including `gov.uk`,
   `assets.publishing.service.gov.uk`, `npsa.gov.uk`, `gao.gov`,
   `discovery.ucl.ac.uk`, `popcenter.asu.edu`, `eff.org`, `frontex.europa.eu`,
   `mdpi.com`, `en.wikipedia.org` and `theguardian.com`. The Keval & Sasse PDF,
   the Gill & Spriggs PDF and the Norris & Armstrong chapter were all identified
   and then refused at the proxy.

**Consequently, the epistemic status of every claim below is marked**, and the
marks are load-bearing:

| Mark | Meaning |
|---|---|
| **[Q]** | Verbatim quotation retrieved this session from the linked source, or carried forward from a sibling dossier in this directory that retrieved it. Safe to quote with the link. |
| **[X]** | Quotation carried forward from `R03`/`R05`/`R06`, which flagged its own retrieval caveats. Re-verify against the primary PDF before external use. |
| **[VERIFY]** | A specific factual claim I believe to be correct from professional knowledge but **could not retrieve this session**. Treat as a hypothesis with a named place to check it. |
| **[lore]** | Practitioner judgement, not a citable fact. Included because it is what a veteran would say, and because pretending otherwise would be worse. |

**Nothing below is a fabricated quotation.** Where I could not obtain wording, I
describe the content and mark it, rather than inventing a sentence and putting
quote marks round it. Several widely-repeated claims in the original brief for
this document turned out to be **wrong on retrieval**, and those corrections are
among the more valuable outputs here — see §1.1 on Westminster's actual camera
count and §11.4 on the Home Office CCTV evaluation.

---

## 1. Hop chain: how this document was built

The research design was a seven-to-eight-hop descent per user group, from
"who are they" to "what would they ask a vendor". The full chain with per-hop
findings and dead ends is **Appendix A (§16)**. The shape, stated once:

```
HOP 1  user group            → who employs them, how many, what they're paid
HOP 2  doctrine / guidance   → the document their manager is judged against
HOP 3  tenders               → what that doctrine becomes when it must be bought
HOP 4  post-implementation   → what the same organisation said afterwards
HOP 5  academic ethnography  → what researchers saw that the PIR omitted
HOP 6  incident inquiries    → what a court or inquiry found when it failed fatally
HOP 7  vendor questions      → what the survivors of hops 4–6 now ask suppliers
HOP 8  simulator demands     → what could only be answered by synthetic evidence
```

The hop that repeatedly produced the most value was **HOP 6 → HOP 7**: inquiry
findings are the only public documents in this field where a named organisation
is compelled to describe its own surveillance operation honestly, under legal
pressure, with the consequences visible. Marketing describes intent; tenders
describe aspiration; inquiries describe reality.

---

## 2. User group (a): the public-space CCTV control-room operator

### 2.1 Who they actually are, and the scale correction

**The scale claim in the brief for this document is wrong, and the correction
matters commercially.** The "~5,000-camera Westminster" figure is not supportable
for Westminster's monitored public-realm estate. What retrieval actually shows is
an estate two orders of magnitude smaller, being rebuilt from near-zero:

> **[Q]** Westminster "has developed a new, high-tech CCTV system with the first
> 100 cameras being fully deployed across the city, with plans to expand the
> Council's public realm CCTV network to 200 cameras", with "100 additional
> cameras by Spring 2026". The system "is monitored at Hammersmith and Fulham
> Council's control centre, with Westminster City Council investing a further
> £150,000 to support the collaboration, which has created **five new full-time
> roles for system operators and a CCTV manager**", and the cameras are
> "actively monitored by trained CCTV operators 24 hours a day, seven days a
> week."
> — **confirmed verbatim on the OJP/NCJRS abstract page** `[audit R4 2026-09-26]` (was: search extraction over
> [Westminster Labour, Feb 2025](https://www.westminsterlabour.org.uk/issues/crime-and-public-protection/2025/02/07/100-more-cctv-cameras-in-westminster-labours-crackdown-on-crime-and-asb/);
> [Westminster City Council CCTV service](https://www.westminster.gov.uk/leisure-libraries-and-community/crime-and-community-safety/cctv-service);
> [Networking+](https://networkingplus.co.uk/news-details?itemid=6273&post=westminster-to-become-safer-city-with-new-cctv-815121);
> and the £1.2m integrator award to North
> ([Comms Business](https://www.commsbusiness.co.uk/content/news/north-awarded-12-million-cctv-contract-by-westminster-city-council/)).
> Also note the analytics content of the new build: cameras "feature specialist
> audio and noise detection AI technology that will alert operatives to loud
> noise complaints".

**Read that paragraph as a product requirement, because it is one.** The unit of
sale in UK local-authority CCTV in 2025–26 is not "5,000 cameras and a hundred
operators". It is **200 cameras and six people, one of whom is the manager, split
across a 24/7 rota — so roughly one operator on shift at any moment**, in a
control centre shared with another borough. Divide it out: a single operator is
nominally responsible for ~200 cameras, 24/7, in a multi-tenant room where the
neighbouring authority's estate competes for the same attention. Against the
R03 §5 finding that trust collapses after three or four false alarms, the
permissible nuisance-alarm budget for an analytics product sold into this
customer is **single-digit alarms per shift, total, across the whole estate.**

Two further structural facts about this user:

- **Shared/outsourced control rooms are now the norm, not the exception.** The
  Westminster→Hammersmith & Fulham arrangement is one instance of a
  decade-long consolidation: districts pooling into county or partnership hubs
  (the Thames Valley CCTV Partnership was named in tender retrieval as the host
  West Oxfordshire joined). **[Q]** — *"Many council upgrade projects involve
  connecting systems to shared monitoring arrangements, either council-operated
  control rooms or police-hosted CCTV hubs, such as West Oxfordshire's upgrade
  which joined the Thames Valley CCTV Partnership"* (search extraction over
  [FVS](https://www.fvs-cctv.com/blog/supporting-local-authorities-with-high-street-surveillance)).
  **Commercial consequence:** your analytics product is being evaluated by a
  manager who does not own the cameras, cannot change their placement, and must
  satisfy several authorities' differing codes of practice from one screen wall.
  **Multi-tenancy, per-tenant configuration and per-tenant audit are functional
  requirements on day one**, not enterprise features for version three. This is
  the same conclusion R05 §1.4 reached from the EUROSUR side; the fact that it
  arrives independently from a London borough is what makes it a real
  requirement.
- **The operator is a licensed, low-paid, high-turnover shift worker.** The UK
  regulatory floor: **[Q]** the SIA **Public Space Surveillance (CCTV)** licence
  costs **£204**; training is "3–4 days", learners "are expected to undertake
  approximately **31 hours of learning** in total, with a minimum of **22 contact
  hours**"; UK pay "ranges from **£15 to £20 per hour**", entry-level £14–£16
  (search extraction over
  [SIA Training Hub](https://siatraininghub.uk/cctv-operator-training-2026/),
  [Get Licensed](https://www.get-licensed.co.uk/licence/cctv-licence),
  [Tavcom](https://www.tavcom.com/courses/cctv-operator-training-course-public-space-surveillance-for-sia-licence/)).
  The same search explicitly returned that it "did not contain specific
  information about operator turnover rates" — **an absence worth recording**,
  because high turnover in this role is universally asserted in the trade press
  and, as far as this session could establish, **never publicly quantified**.
  **[VERIFY]** — the places to look are the SIA's own licensing statistics and
  the BSIA/Skills for Security workforce reports.

**The design consequence of "31 hours of learning and £15/hour" is the single most
under-appreciated fact in this market.** [lore] A vendor demo tuned by an ML
engineer with a PhD is being handed to someone with four days of formal training,
on night shift, at hour six, on a system they did not choose. Every configuration
surface you expose — a confidence threshold, a polygon, a dwell time, a
sensitivity slider — is a surface on which the system will be mis-set and then
blamed. The correct design posture is **not "expose the knobs"; it is "ship
site-appropriate defaults, log every deviation from them, and make the
mis-configuration visible to the manager"**. Half the field failures attributed to
model quality are configuration failures with no audit trail.

### 2.2 The doctrine layer: what governs them

The governing UK instrument is the **Surveillance Camera Code of Practice**,
issued under the **Protection of Freedoms Act 2012**:

> **[Q]** The code contains "**12 guiding principles**", provides guidance "on the
> appropriate use of surveillance camera systems by local authorities and the
> police", and the guiding principles "draw together good practice and existing
> legal obligations to create a regulatory framework which can be understood by
> system operators and the public alike". Procedurally: the updated code was
> "laid before both Houses on **16 November 2021**", neither House objected, and
> "it came into effect on **12 January 2022**". Critically for who must care:
> "**Section 33(5)** places Local Authorities on a list of 'relevant authorities'
> who MUST pay due regard to the Code", and "relevant authorities are encouraged
> to seek advice from the Commissioner and other regulators **before any trial or
> pilot of new technology is undertaken in a public place**."
> — search extraction over
> [GOV.UK amended code](https://www.gov.uk/government/publications/update-to-surveillance-camera-code/amended-surveillance-camera-code-of-practice-accessible-version),
> [guide to the 12 principles (PDF)](https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/1054263/Code_of_Practice-guide_to_the_12_principles.pdf),
> [House of Lords Library, regret motion](https://lordslibrary.parliament.uk/surveillance-camera-code-of-practice-regret-motion/),
> [local-authority guide](https://www.gov.uk/government/publications/surveillance-camera-code-of-practice-guidance-for-local-authorities/surveillance-camera-code-of-practice-a-guide-for-local-authorities-accessible).

And Principle 1, carried forward from R03 §9.1: **[X]** *"Use of a surveillance
camera system must always be for a specified purpose which is in pursuit of a
legitimate aim and necessary to meet an identified pressing need."*

**That last retrieved sentence — "seek advice… before any trial or pilot of new
technology is undertaken in a public place" — is the single most commercially
important sentence in this section.** It means that in the UK local-authority
market, *the pilot itself is a regulated act*. A vendor who arrives with "let's
just run it for two weeks and see" is asking a named officer to commit a
compliance breach on their behalf. The correct offer is the opposite: **"here is
our DPIA template, here is our synthetic-data evidence pack, and here is a
shadow-mode configuration that produces no operational decisions"** — a
proposition that a simulator makes cheap and that a real-footage-only vendor
cannot make at all. This is the clearest instance in this whole document of
regulation creating a market for synthetic evaluation evidence.

### 2.3 The tender layer: what they write down

Retrieval over UK Find-a-Tender in 2025 gave four genuinely instructive data
points about what this user buys **[Q]**, from search extraction over
[Find a Tender](https://www.find-tender.service.gov.uk/):

1. **Kent County Council** ran *"CCTV, Security & Access Solutions"* (Feb 2025) —
   i.e. analytics is procured inside a **facilities-and-access bundle**, not as an
   AI purchase ([notice 005344-2025](https://www.find-tender.service.gov.uk/Notice/005344-2025)).
2. **The Police & Crime Commissioner for Sussex** ran an *"Automated Video
   Redaction Solution"* (2025), and the procurement "appears to include
   multi-stage procurement including demonstrations and user testing"
   ([notice 029956-2025](https://www.find-tender.service.gov.uk/Notice/029956-2025?origin=SearchResults&p=1)).
3. **West Yorkshire Police** procured *"AI CCTV Analytic Software and Associated
   Hardware to ingest video footage making it searchable by events and
   descriptive factors, requiring a minimum 5 users and supporting hardware."*
4. **Supply-chain security is now a baseline gate:** *"On most active council
   tenders in 2025–26, NDAA compliance is either a stated requirement or
   effectively expected."*

**Four readings, each of which should change how a product is pitched.**

- **The highest-volume "AI video" procurement in UK policing right now is
  retrospective search and redaction, not real-time alerting.** "Searchable by
  events and descriptive factors" is person-attribute retrieval (R05 Part B
  §10); "automated video redaction" is a workload product driven by disclosure
  obligations. A vendor whose only story is live threat alerting is pitching into
  the smaller and slower-moving half of the budget. [lore]
- **"Minimum 5 users"** tells you the true shape of demand: a handful of named
  analyst seats, not an enterprise rollout. Price and package accordingly.
- **"Demonstrations and user testing" as formal procurement stages** means your
  evaluation will be run by the people in §2.1 — four-day-trained shift staff —
  on data they choose. Your win condition is *their* success in a scripted task,
  not your metric on your benchmark.
- **NDAA compliance** is a hardware-provenance gate that catches analytics vendors
  who assume the camera layer is someone else's problem. The clause is US FY2019
  NDAA §889, implemented by FAR 52.204-25, which names Hytera, Hikvision and Dahua
  video surveillance equipment [audit 2026-09-26: confirmed at acquisition.gov].
  **[VERIFY]** whether UK notices reference it directly or via the national-security
  exclusion/debarment provisions of the Procurement Act 2023 [audit 2026-09-26: was
  "2022 Procurement Act"; Royal Assent 26 Oct 2023].

### 2.4 The post-implementation layer: the Home Office's own verdict

The reference point every UK CCTV manager over 45 has heard of, and the one that
still shapes business cases:

> **[Q]** Martin Gill and Angela Spriggs, *Assessing the Impact of CCTV*, **Home
> Office Research Study 292**, February 2005 [audit 2026-09-26: was "January"; title page reads February 2005], 160 pages. The authors "undertook an
> analysis of the effectiveness of CCTV systems, both with respect to the impact
> on crime as recorded by the police and wider measures based on victimization
> rates, fear of crime and other information collected via local surveys."
> Their framing conclusion: "While CCTV can be a powerful tool in combating
> crime, the contexts in which CCTV systems operate are very variable, as are the
> systems themselves." The analysis covers "13 out of the 684 CCTV projects
> undertaken."
> — search extraction over
> [HORS 292 (PDF)](https://popcenter.asu.edu/sites/g/files/litvpz3631/files/Responses/video_surveillance/PDFs/Gill&Spriggs_2005.pdf),
> [OJP abstract](https://www.ojp.gov/ncjrs/virtual-library/abstracts/assessing-impact-cctv),
> [Semantic Scholar](https://www.semanticscholar.org/paper/Assessing-the-impact-of-CCTV-Gill-Spriggs/39d5c2c01ec6ae86ebbb4deed7822bf31af0c317).

**[VERIFY] — and this is an important correction to the brief.** The widely
circulated summary of HORS 292 is that *"only one of thirteen systems showed a
statistically significant reduction in crime attributable to CCTV"*, and that
where effects were found they were concentrated in car parks. I could **not**
retrieve that sentence or its numbers this session (the PDF host is
egress-blocked). **Do not put a figure on it without opening the PDF.** What *is*
retrievable and safe is the authors' own hedged framing quoted above, plus the
structural finding that context and system variability dominate — which is the
part that actually matters for us anyway.

**Why the 2005 study is still the most useful single document for a vendor.** Its
argument is not "CCTV doesn't work". It is that **outcome variance is explained by
implementation, not by technology** — camera siting, lighting, control-room
staffing, police-liaison arrangements, public awareness, and whether the system
was ever evaluated against a stated objective. Every one of those is a variable
a simulator can hold constant or sweep. A vendor who says *"HORS 292's lesson is
that siting and staffing dominated the outcome, so here is a simulator-derived
camera-placement and operator-load study for your specific site"* is speaking
directly into a twenty-year-old institutional wound. [lore]

### 2.5 The ethnography layer: what researchers saw in the room

This is the layer vendors never read, and it is where the real user requirements
are.

**Norris & Armstrong, *The Maximum Surveillance Society: The Rise of CCTV*
(Berg, September 1999)** — based on "extensive fieldwork on automated surveillance
in Britain over a two-year period". The quantitative core: the research "yielded
data on **888 targeted surveillances**, with **711** surveillances documenting
persons identified with basic demographic data including age, race, sex, and
appearance", and the headline finding that there is **[Q]** *"a massively
disproportionate targeting"* of young black males *"for no other reason than
their membership of that particular group"* (search extraction over the
[Internet Archive record](https://archive.org/details/maximumsurveilla0000norr),
[Taylor & Francis](https://www.taylorfrancis.com/books/mono/10.4324/9781003136439/maximum-surveillance-society-gary-armstrong-clive-norris),
and Norris & Armstrong's chapter
[*CCTV and the Social Structuring of Surveillance*](https://popcenter.asu.edu/sites/g/files/litvpz3631/files/library/CrimePrevention/Volume_10/06-NorrisArmstrong.pdf)).

The associated concept — **"categorical suspicion"**, the practice of selecting
targets by group membership and appearance rather than by observed behaviour — is
the one to know by name. **[VERIFY]** the exact page and phrasing; the concept is
Norris & Armstrong's and it is the standard citation in the surveillance-studies
literature.

**Why this is not merely an ethics point but a data-engineering point, and the
most important paragraph in this document.** If operator attention is
systematically skewed by group membership, then **every artefact produced by
operator attention is skewed the same way**: the alarm log, the incident report,
the "interesting clip" archive, the labelled training set built from any of them.
R03 §4.4 makes the analogous argument about predictive policing's feedback loops.
Combine the two and you reach a hard conclusion a vendor should state out loud
in the first meeting: **training a behaviour analytic on a customer's historical
operator-generated labels is training a model to reproduce Norris & Armstrong's
finding, at machine scale, with an audit trail.** The principled alternative is
a generator whose labels come from its own intent rather than from anyone's
suspicion — which is precisely what this repository builds. That is the strongest
ethical *and* commercial argument for a simulator in this entire document.

**Gavin J. D. Smith, *Opening the Black Box: The Work of Watching*
(Routledge, 2012/2016)** — "a fine-grained ethnography of the culture of CCTV
operation in the UK". The retrieved description of the labour is worth quoting
because its vocabulary is unlike any vendor datasheet: the book "excavates the
social relations entwining the everyday application of CCTV, with attention
focusing on the labour exerted by camera operators as they source and process
distanced spectacles. These workers are paid to **scan monitor screens in search
of disorderly vistas, visualizing stimuli according to its perceived riskiness
and/or allurement**", it "contemplates the **seductive and traumatic** dimensions
of monitoring telemediated 'riskscapes'", positions operators as **"'vicarious'
custodians of a precarious social order"**, and reveals the work of watching to
be "as much about **managing external disturbances on the street as managing
internal disruptions in the self**" **[Q]** (search extraction over
[Routledge](https://www.routledge.com/Opening-the-Black-Box-The-Work-of-Watching/Smith/p/book/9781138200043),
[Taylor & Francis](https://www.taylorfrancis.com/books/mono/10.4324/9780203519387/opening-black-box-gavin-smith),
[Oxford Centre for Criminology review](https://blogs.law.ox.ac.uk/centres-institutes/centre-criminology/blog/2014/11/opening-black-box-work-watching),
[Lee's review in *Journal of Sociology*](https://journals.sagepub.com/doi/10.1177/1440783315595327)).

Three product consequences, each of which contradicts a common design instinct
**[lore]**:

1. **"Perceived riskiness and/or allurement."** Operators watch what is
   *interesting*, and interest is not risk. This is the human mechanism behind
   the thing every manager complains about and no vendor designs for: the camera
   that stays parked on the busy square while the alarm zone goes unwatched. An
   analytic that competes for the same attention loses; an analytic that
   **reclaims the un-interesting** (empty perimeters at 04:00) wins.
2. **"Traumatic" and "internal disruptions in the self."** Operators witness
   suicides, assaults and deaths, repeatedly, alone, at night, with no clinical
   support structure. **[VERIFY]** the CCTV-specific PTSD/vicarious-trauma
   literature. A product feature falls straight out of this: **the system should
   be able to take the watching burden during known-distressing sustained
   incidents** (a person on a bridge parapet; a body in view awaiting
   recovery) — continuous automated monitoring of a static tragic scene is a
   genuinely humane application and nobody markets it. That is an unclaimed
   position.
3. **Operators are "vicarious custodians" with no authority.** They see, they
   report, someone else acts or doesn't. The most-cited operator frustration in
   this literature is not missing events; it is **reporting an event and nothing
   happening.** A product that improves detection without improving the
   downstream handover has made the core grievance worse by increasing the number
   of ignored reports. Design the handover, not just the alarm.

**Keval & Sasse, "Not the Usual Suspects": A Study of Factors Reducing the
Effectiveness of CCTV, *Security Journal* 23(2):134–154 (2010)** — the single
most directly useful academic paper for a vendor building for this user, because
its method is a requirements-elicitation exercise in disguise:

> **[Q]** The study "investigated the relationship between CCTV system design and
> the performance of operator tasks through **structured observations and
> interviews with 13 managers and 38 operators at 13 CCTV control rooms**". The
> identified failures: "**poor configuration of technology, poor quality video
> recordings, and a lack of system integration, as well as poor stakeholder
> communication and too many cameras with too few operators**."
> — search extraction over
> [UCL Discovery record](https://discovery.ucl.ac.uk/id/eprint/19823/),
> [the PDF](https://discovery.ucl.ac.uk/19823/1/Keval_Sasse_Not_the_Usual_Suspects_Security_Journal_2010.pdf),
> [Springer](https://link.springer.com/article/10.1057/palgrave.sj.8350092),
> [OJP abstract](https://www.ojp.gov/ncjrs/virtual-library/abstracts/not-usual-suspects-study-factors-reducing-effectiveness-cctv)).

**Memorise that five-item failure list; it is the de facto user requirement
specification for this market, and note what is absent from it.** Not one of the
five failures is "the detection algorithm was insufficiently accurate". They are,
in order: **configuration, recording quality, integration, communication,
staffing ratio.** A vendor optimising detection accuracy is optimising the sixth
thing on a five-item list. The corresponding requirement set is therefore:

| Keval & Sasse failure | What it demands of a product | What it demands of a simulator |
|---|---|---|
| Poor configuration of technology | Self-configuring or site-survey-derived defaults; configuration audit; drift alerts | Sweep configuration space; show cost of mis-set dwell/threshold/polygon |
| Poor quality video recordings | Operate at the customer's real bitrate/codec/resolution, not the demo's | Render degraded chains: compression, low light, defocus, motion blur (see [R04](./R04_degraded_imaging_and_sim2real.md)) |
| Lack of system integration | ONVIF/VMS/PSIM/C2 integration as a first-class deliverable | Emit alarms in the customer's schema, testable offline |
| Poor stakeholder communication | Evidence packages and handover artefacts, not just alarms | Generate the full evidential chain synthetically |
| Too many cameras, too few operators | Alarm budget per shift as the governing metric | Simulate operator load at realistic ratios |

---

## 3. User group (b): the CNI security manager

### 3.1 Who they are

Not an operator, not a CISO. The CNI physical-security manager is typically an
ex-military or ex-police head of security at a licensed or regulated site — a
nuclear licensed site, a National Grid substation portfolio, a water treatment
works, an airport, a port, a rail terminus, a data centre campus — reporting into
operations or risk rather than into IT, holding a budget that is small relative to
the asset value it protects, and **judged on a regulatory return rather than on
crime reduction.** That last clause is the whole difference from §2. The local
authority manager is judged on outcomes and public confidence. The CNI manager is
judged on **demonstrable compliance with a security plan approved by a
regulator**, and on the absence of a reportable event.

**The single most useful thing to understand about selling analytics to this
user: their dominant fear is not the attack. It is the regulator's next
inspection, and the possibility that your product creates a finding.** [lore] An
unassured, undocumented, un-patchable AI box inside the security boundary is a
liability on an inspection report before it is a capability. Everything in §3.4
follows from that.

### 3.2 The doctrine layer

Carried forward from R05 §1.1–1.2, which retrieved the primary wording, and
extended here on the organisational side.

**NPSA — the National Protective Security Authority**, formerly CPNI, hosted by
MI5, is the national technical authority. Its framing of perimeter detection is
the sentence to internalise: PIDS is **[X]** *"a generic term which covers a wide
range of technologies designed to provide **advance warning** of an intruder
gaining access to a secure area"*
([NPSA PIDS](https://www.npsa.gov.uk/building-protection/video-surveillance-access-control-detection-control-rooms/perimeter-intrusion-detection-pids);
[Guide to PIDS PDF](https://www.npsa.gov.uk/system/files/documents/2c/80/Guide-to-PIDS.pdf)).
**Advance warning, not answer.** The corollary quoted in R05 is that alarms must
be *verified through the use of CCTV* before response — i.e. **the customer's own
national authority has written down that your analytic is a cue and a human
closes it.** Quote this back to them; it signals you understand your place in
their architecture, and it is also your liability firewall.

The guidance family a credible vendor can name without notes:

| Guidance | What it is | Why the vendor cares |
|---|---|---|
| **PSeMS / Protective Security Management Systems** | NPSA's management-system framework for protective security, modelled on ISO-style management systems: policy, risk assessment, controls, competence, assurance, continual improvement **[VERIFY]** exact element list at [npsa.gov.uk](https://www.npsa.gov.uk/) | Your product must produce **evidence artefacts that slot into a management system** — logs, competence records, performance reviews. "It detects things" is not a PSeMS input. |
| **CAPSS — Cyber Assurance of Physical Security Systems** | Assurance scheme under which **[X]** *"perimeter intrusion detection hardware and software are examples of potential products available to be assured"* and passing products *"will be entered into the NPSA Catalogue of Security Equipment (CSE)"* ([NPSA CAPSS](https://www.npsa.gov.uk/cyber-assurance-physical-security-systems-capss-evaluations)) | The gate that kills analytics startups. R05's warning stands: *"we're an analytics layer, not a security product" is not an accepted answer.* |
| **CSE — Catalogue of Security Equipment** | The procurement catalogue; entry means tested-and-published components | **A procurement gate, not a performance claim.** Read a CSE entry to find *which firmware was tested*. |
| **i-LIDS** | Home Office imagery benchmark, five scenarios (four event-detection + multi-camera tracking) [audit 2026-09-26: was "four"; i-LIDS User Guide lists five], sequestered footage, event-level scoring with a 10-second tolerance ([R03 §2](./R03_behaviour_intent_anomaly_detection.md)) | The only recognised UK pass/fail for operational alerting. Its corpus design — 24 h per scenario, all weather, all times, 2–3 views, deliberate non-alarm events — **is the specification for a synthetic corpus.** |
| **Guarding / Security-minded approach** | NPSA guidance on guard-force deployment, and on managing the information *about* a site that an adversary could exploit **[VERIFY]** | The "security-minded approach" is why some customers will not let you take site imagery off-premises at all — **the strongest possible driver for synthetic surrogate data.** |
| **ONR SyAPs** | Office for Nuclear Regulation Security Assessment Principles, the nuclear-sector security framework with associated Technical Assessment Guides **[VERIFY]** the CCTV/detection-specific TAG reference at [onr.org.uk](https://www.onr.org.uk/) | Nuclear customers will ask which SyAPs fundamental principle your system supports and how it is assured. Getting the acronym right is the credibility test. |
| **Sector regulators** | Ofgem/NESO and the energy-resilience regime; DWI/water; DfT for aviation and maritime security (with its own directions regime); NIS/NIS2-equivalent duties | Determines who signs off, and what "reportable" means. |

### 3.3 The incident layer: what has actually happened to them

These are the events CNI managers reference in internal business cases. I have
retrieved wording for none of them this session, so all are marked, but the
*pattern* they establish is robust and is what matters.

- **Moore County, North Carolina, December 2022** — gunfire directed at two Duke
  Energy substations caused a multi-day outage affecting tens of thousands of
  customers; no suspect was publicly identified. **[VERIFY]** all figures and the
  current investigative status. **The relevant lesson for analytics is not
  detection but *geometry*:** the attack was a standoff attack on unmanned assets
  through a fence, in darkness, in a rural setting where the nearest responder was
  a long drive away. An analytic that alarms on fence contact is irrelevant to it.
  What matters is **wide-area, long-range, low-light detection of a human
  loitering or a vehicle stopping outside the fence line** — i.e. the standoff
  approach phase, at ranges and light levels where real training data barely
  exists. That is a synthetic-data problem by construction.
- **A cluster of US substation intrusions and attacks 2022–2023**, and the FERC /
  NERC CIP-014 physical-security standard regime that governs the response
  **[VERIFY]** — CIP-014 requires risk assessment and physical-security plans for
  critical transmission stations, and is the clause a US energy customer will cite
  when asking whether your product is an acceptable control.
- **Nord Stream pipeline damage, September 2022** — subsea CNI, attributed
  variously and still contested **[VERIFY]**. Its effect on the market is real
  regardless of attribution: it moved "CNI includes things nobody is watching"
  from theory to board agenda across European utilities, and it is the origin of
  a lot of current spend on **unmanned, remote, low-bandwidth monitoring** of
  assets with no operator nearby.
- **The North Hyde substation fire of 20 March 2025 and the closure of Heathrow
  Airport on 21 March.** [audit 2026-09-26: fire date was given as 21 March; NESO's
  final review attributes it to a transformer HV-bushing failure, most likely moisture
  ingress first flagged in 2018 oil samples, i.e. an equipment/maintenance failure,
  not an attack; ~70,000 customers affected (neso.energy final report)] **[VERIFY] — and the brief's framing of this as "substation arson"
  is not established and should not be repeated.** What I can state from
  professional knowledge is that a fire at an electrical substation serving the
  Heathrow area caused the airport's closure for most of a day with very large
  consequential disruption, and that a review process followed (NESO was
  commissioned to review the incident; Ofgem and the airport's own review were
  involved). **The publicly reported cause was an equipment fault, not a
  deliberate attack, as far as I am aware.** Check [ofgem.gov.uk](https://www.ofgem.gov.uk/),
  [neso.energy](https://www.neso.energy/) and the Kelly Review commissioned by
  Heathrow before asserting anything. **Why a vendor should care even though it
  was probably not an attack:** it is now the canonical UK example of
  **single-point-of-failure interdependency** between CNI sectors, and it has
  made "what else depends on this asset" a question security managers are being
  asked by their boards. That is a *situational-picture* question — exactly the
  EUROSUR-style aggregation problem in R05 §1.4 — and it is being asked by people
  who previously only bought fences.

### 3.4 What the CNI manager therefore asks a vendor

Distilled from the above; all **[lore]** but high-confidence:

1. Is it in the **CSE**? If not, what is your **CAPSS** plan and timeline?
2. What happens to the **operational network** if your box is compromised? Show
   me the network diagram and the data flows, including any egress.
3. Does anything leave site? (For many nuclear and defence sites the answer must
   be *no*, which rules out cloud inference and, by extension, most of the
   false-alarm-filtering market described in R03 §5.3.)
4. What is the **nuisance-alarm rate on my perimeter**, measured over 30 days,
   broken out by zone and hour, with the weather record? (R05 §1.6 — "any vendor
   who quotes you a NAR figure without a site survey is quoting a lab number".)
5. What does it do when a camera is **dirty, misaligned, frozen, or dark**? Can it
   tell me that, and does that count as an alarm or a fault?
6. Who is **accountable** if it misses, and what does my inspection report say
   about it?
7. Can you produce the evidence a **PSeMS** assurance review needs, on demand,
   without me building a spreadsheet?
8. What is the **maintenance and re-calibration burden** per camera per year?

**Requirement 5 deserves separate emphasis because vendors consistently miss it.**
For a CNI customer, **"the camera is not working" and "there is an intruder" are
both alarms, and the first is the more common and more actionable.** Availability
monitoring — tamper, defocus, occlusion, scene change, PTZ home-position drift,
signal loss — is often worth more to this buyer than behaviour classification,
is far easier to get right, is uncontroversial with regulators and unions, and
maps onto the *camera tampering* vocabulary R03 §1.2 already establishes. **[lore]
The shortest credible path into a CNI account is health-and-integrity analytics,
with behaviour analytics sold later on the trust that earns.** R05 §1.3's lesson
about US border towers — that the dominant failure mode is "uptime, power, comms,
calibration drift, and maintenance economics", not classifier recall — is the same
finding arriving from a different continent.

---

## 4. User group (c): border agencies

### 4.1 Who they are and what they are measured on

Border surveillance users split into three roles that are constantly conflated in
vendor pitches and must be kept apart:

- **The watchkeeper** in a maritime or land-border operations room, fusing radar,
  AIS, EO/IR, aerostat or UAS feeds into a picture and cueing assets. Closest
  analogue to the CCTV operator, but with far longer detection ranges, far worse
  imagery, and a maritime-safety duty layered on top of the enforcement task.
- **The interdiction commander** deciding which asset goes where. Cares about
  *time-to-intercept* and *asset utilisation*, not detection metrics.
- **The analyst / risk-analysis unit** producing the periodic picture, trend and
  tasking products. Cares about consistency, provenance and comparability over
  time far more than about any single detection.

**Doctrinal vocabulary and KPIs.** The terms a border customer uses, and what they
mean operationally **[lore]** except where marked:

| Term | Operational meaning | Trap for the vendor |
|---|---|---|
| **Situational awareness / situational picture** | **[X]** EUROSUR's legally defined deliverable: *"an aggregation of geo-referenced near-real-time data and information received from different authorities, sensors, platforms, and other sources"* ([Statewatch](https://www.statewatch.org/analyses/2019/monitoring-secondary-movements-and-hotspots-frontex-is-now-an-internal-surveillance-agency/)) | It is a *data product with provenance and release marking*, not a dashboard. Multi-authority aggregation implies multi-tenancy and layer-level access control. |
| **Detections** | Events observed | Cheap to inflate. Detections are an *input* metric; nobody senior is impressed by them. |
| **Interdictions / apprehensions** | Events acted upon successfully | The number the agency is judged on. Your product only affects it if it changes *what an asset does*. |
| **Impedance and denial** | Making a route slow, costly or unattractive rather than intercepting on it | A **deterrence** metric, therefore nearly unmeasurable, therefore the refuge of programmes that cannot show interdiction gains. Recognise it as such. |
| **Situational awareness gap / domain awareness** | Areas and times with no coverage | The honest procurement driver, and the one a simulator can address head-on via coverage modelling. |
| **False alarms / nuisance** | See R05 §1.6 | At border scale, the operator load metric is alarms per watchkeeper per shift, not per camera-hour. |

### 4.2 UK: the Channel and the small-boats problem

**[VERIFY] throughout this subsection — no retrieval was possible.** The
operational facts as I understand them: Home Office and Border Force maritime
surveillance of the Dover Strait has been delivered through a mix of
vessel-based radar and EO/IR, aerial surveillance including contracted
long-endurance UAS, and coastal sensors, with **Tekever** publicly reported as a
supplier of maritime surveillance UAS services to the Home Office, alongside
earlier contracted manned-aircraft and aerostat trials. Check Home Office
contract award notices on
[Find a Tender](https://www.find-tender.service.gov.uk/) and
[Contracts Finder](https://www.contractsfinder.service.gov.uk/), and
[tekever.com](https://www.tekever.com/).

**The analytically interesting feature of this user, which generalises.** The
Channel task is *not* a detection problem in the sense the CV literature means.
Small boats in the Dover Strait are detected readily; the hard problems are
**(i)** counting people on a crowded RHIB from a long-range oblique EO/IR view in
sea state and haze, for a **safety-of-life** decision about how many rescue
places are needed; **(ii)** maintaining track continuity across sensor handovers
and long gaps; **(iii)** distinguishing the target vessel from hundreds of
legitimate craft; and **(iv)** producing a record defensible in later legal and
inquest proceedings. **Person-counting under extreme degradation, with a safety
consequence and an evidential obligation** — that is a simulator problem, and it
is the sharpest example in this document of a real requirement that public
datasets do not address at all. It is also where the humanitarian critique bites
hardest: the same sensor output is simultaneously a rescue instrument and an
enforcement instrument, and the agency is legally and politically exposed on
both. Any vendor pitching here must be able to talk about the rescue duty first
and without prompting. [lore]

### 4.3 US: the tower programmes and the audit trail

R05 §1.3 covers the technical lineage. The **user-side** findings, carried
forward:

> **[X]** GAO describes the Integrated Surveillance Towers programme as
> "*803 fielded towers located along US borders that detect items of interest,
> such as people or vehicles*" [audit R4 2026-09-26: verbatim on p.98 of
> GAO-26-108118; p.99 of the same report says 830 fielded + 175 planned, 2,300
> by FOC March 2034], with Autonomous Surveillance Towers providing
> "*autonomous surveillance operations 24 hours per day, 365 days per year*"
> ([FedScoop](https://fedscoop.com/anduril-sentry-towers-cbp/);
> [EFF 2024](https://www.eff.org/deeplinks/2024/10/us-border-surveillance-towers-have-always-been-broken)),
> the programme "*expected to be completed by March 2034, with 2,300 deployed by
> that date*" **[VERIFY]**, and a ~$1bn expansion reported in 2026
> ([Reason](https://reason.com/2026/07/30/homeland-security-is-spending-1-billion-on-autonomous-border-surveillance-towers/),
> [EFF 2026](https://www.eff.org/deeplinks/2026/07/explosion-surveillance-towers-coming-us-borders-costing-over-1-billion)).
> The EFF's summary headline of two decades of auditing is
> "*U.S. Border Surveillance Towers Have Always Been Broken*".

**The GAO critique to be able to state precisely, because it is the template for
every effectiveness question you will be asked. [VERIFY] the exact GAO report
numbers and wording** (`gao.gov` is egress-blocked; search GAO for CBP
surveillance technology, IFT/RVSS/AST effectiveness measurement): the recurring
finding across GAO's border-technology work is **not** that the sensors fail to
detect. It is that **CBP did not define, collect or use metrics that would show
whether the technology contributed to mission outcomes** — no baseline, no
attribution of apprehensions to tower cues, no availability data, no cost per
outcome. And on privacy, the claim carried in R05: **[X] [VERIFY]** *"In 2024,
the Government Accountability Office assessed CBP's surveillance tower programs
against six baseline privacy protections derived from the Fair Information
Practice Principles, and CBP failed all six"*
([EFF](https://www.eff.org/deeplinks/2024/10/us-border-surveillance-towers-have-always-been-broken)).

**Why this is the most useful single thing in the document for a vendor's
pre-sales strategy. [lore]** GAO's criticism is *of the customer, not of the
supplier*, and it creates a demand the supplier can satisfy. A programme office
that has been told twice by its auditor that it cannot demonstrate effectiveness
will pay for **an effectiveness-measurement capability**: instrumented
baselines, cue-to-apprehension attribution, availability and detection
accounting, and repeatable evaluation on known-truth data. A simulator is the
only way to obtain known truth at scale. **Sell the measurement, not just the
model.** The pitch line is: *"we will give your auditor the numbers they asked
you for."*

### 4.4 EU, and the rest of the world

- **Frontex / EUROSUR.** R05 §1.4 has the definitions. The user-side points to add:
  EUROSUR is an **information-exchange obligation on Member States**, so the
  actual user is often a national coordination centre with its own legacy systems
  and its own politics about what it shares upward; and **Eurosur Fusion
  Services** (satellite, vessel-tracking, and related products supplied centrally
  to national users) is the part that most resembles a commercial analytics
  offering **[VERIFY]** at
  [home-affairs.ec.europa.eu](https://home-affairs.ec.europa.eu/policies/schengen/eurosur_en).
  The critical literature is organised and citable
  ([ITSS Verona](https://www.itssverona.it/european-border-surveillance-system-eurosur-and-its-problematic-impact-on-the-rights-of-the-people-on-the-move),
  [Völkerrechtsblog](https://voelkerrechtsblog.org/under-eurosurs-watchful-eye/)) —
  R05's advice holds: **a professional can name the critics unprompted.**
- **"Smart borders" / EES and ETIAS** **[VERIFY]** — the EU's entry/exit and
  travel-authorisation systems are biometric *identity* infrastructure at crossing
  points, a different problem from surveillance analytics, and conflating them in
  a pitch marks you as an outsider.
- **India: BSF and CIBMS** — the Comprehensive Integrated Border Management System,
  a programme to overlay sensors, radar, thermal imaging and command-and-control
  on sections of India's land borders **[VERIFY]** at
  [bsf.gov.in](https://www.bsf.gov.in/) and Indian MHA annual reports. The
  documented pattern in public reporting has been ambitious pilots followed by
  sustainment and integration difficulty across extremely varied terrain —
  the same story as the US towers, in a different climate.
- **Israel's border barriers and "smart fence"** systems, and **Saudi Arabia's
  northern border** programme (the large EADS/Airbus-era integrated border
  project) **[VERIFY]** — both are the reference points for "very long perimeter,
  very high sensor density, very few operators", i.e. the extreme end of the
  cameras-per-operator ratio problem. If you want to know what a 10,000:1 ratio
  forces architecturally, these are the programmes to study.

**The unifying border finding. [lore]** Across UK, US, EU and Asian programmes the
public record shows the same three-part failure signature, and it is *never*
primarily about model accuracy: **sustainment** (power, comms, maintenance,
spares, calibration in hostile environments), **integration** (the new sensor's
picture does not merge with the old one, so operators run two screens), and
**effectiveness measurement** (nobody can show what the money bought). A vendor
whose proposal addresses only detection quality is proposing to solve the one
problem the customer does not have.

---

## 5. User group (d): police

### 5.1 The four distinct police users

"The police" is four customers with incompatible requirements, and treating them
as one is the most common vendor error in this market. [lore]

1. **The force control room / CCTV hub** — live monitoring, often co-located with
   or fed by local-authority estates (§2.1). Requirement: fewer, better alarms,
   and a direct route from alarm to deployable information.
2. **The investigator / video-forensics unit** — retrospective search across
   seized and public footage. This is where the money is (§2.3: West Yorkshire's
   *"searchable by events and descriptive factors"*, Sussex's automated
   redaction). Requirements are **recall over precision**, disclosure integrity,
   chain of custody, and export in a format a court accepts.
3. **The public-order / event commander** — Gold/Silver/Bronze command over a
   planned or spontaneous event (§7). Requirement: crowd density, flow, and
   capacity information at a decision-relevant timescale, plus a defensible log
   of what was known when.
4. **The specialist counter-terrorism and protective-security officer** — hostile
   reconnaissance, Servator-style deployments, and site advice (CTSAs). Requirement:
   corroboration across time and place, and doctrinal defensibility.

### 5.2 Doctrine: Servator, hostile reconnaissance, and the "negate or confirm" rule

Carried from R03 §4.2, because it is the single most important doctrinal
constraint on any behaviour-analytics product sold to UK policing:

> **[X]** Hostile reconnaissance is *"purposeful observation with the intention of
> collecting information to inform the planning of a hostile act against a
> specific target"*
> ([NPSA](https://www.npsa.gov.uk/security-guidance/risks/hostile-reconnaissance)).
> Deterrence is *"the intelligent, co-ordinated promotion of protective security
> provision to the hostile that results in the perception and/or assessment that
> the reconnaissance or the attack itself will fail"*
> ([NPSA](https://www.npsa.gov.uk/specialised-guidance/hostile-reconnaissance/disrupting-hostile-reconnaissance)).
> **Project Servator** is *"a strategic method of policing to deter, detect and
> disrupt a wide range of criminal activity, from pickpocketing and property theft
> to terrorism"*, developed by NPSA with the City of London Police, in which
> *"Servator officers are trained to identify subtle non-verbal signs indicative
> of anxiety and agitation, and they interact with individuals displaying
> suspicious behaviours to **negate or confirm** suspicions"*, and
> *"deployments are unpredictable and intelligence-led"*
> ([NPSA Project Servator](https://www.npsa.gov.uk/national-security-act/countering-threat-sabotage-operations-uk-interests-national-security/project-servator)).
> NPSA explicitly frames control rooms as a disruption resource: guidance covers
> *"utilising existing protective security resources such as CCTV control rooms,
> security officers and corporate communications more effectively to disrupt
> hostile reconnaissance"*.

**Three consequences a vendor must be able to articulate.**

- **"Negate or confirm" is an architectural requirement, not a caveat.** The
  doctrine's behavioural observation is a trigger for a human conversation. A
  product that outputs "this person is conducting hostile reconnaissance" has
  skipped the doctrine's own safeguard. The correct output is *"this identity has
  been present in this zone on four occasions in nine days, each time outside
  operating hours, each time oriented toward the loading bay"* — a **lead for
  enquiry**, expressed in observables.
- **Behavioural-cue detection of emotional state is scientifically dead and you
  must say so before the customer's lawyer does.** The GAO TSA SPOT finding
  carried in R03 §4.3: **[X]** the human ability to identify deception from
  behavioural indicators is *"the same as or slightly better than chance (54
  percent)"*, and *"10 years after the development of the SPOT program, TSA cannot
  demonstrate the effectiveness of its behavior detection activities"*
  ([GAO-14-159](https://www.gao.gov/products/gao-14-159),
  [GAO-14-158T](https://gao.gov/products/GAO-14-158T),
  [GAO-17-608R](https://www.gao.gov/products/gao-17-608r)).
  **Volunteering this citation is the highest-trust move available to a vendor in
  a policing room.** It says: we know which of our competitors' claims are
  fraudulent, and we are not making them.
- **Servator itself has an independent evaluation** and a professional should have
  read it: [a comparison of Project Servator and routine stop and search outcomes
  in the City of London](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11755829/).

**Other police doctrine to be able to name [VERIFY]:** the College of Policing
**Authorised Professional Practice** on information management and on public
order (APP is the doctrinal source police officers actually cite); **NPCC**
national positions on new technology; the Home Office **Safer Streets** funding
stream, which is the mechanism through which much local CCTV and lighting
capital actually arrives, and which therefore drives the **timing** of local
procurements far more than any technology cycle.

### 5.3 Live facial recognition: the accountability precedent

**[VERIFY] throughout — no retrieval available.** The essential chronology a
vendor must know, because every AI-video conversation with a UK police customer
now happens inside it:

- **South Wales Police / *Bridges*** — the Court of Appeal's 2020 judgment on
  live facial recognition, which found the particular deployment unlawful on
  grounds including insufficiently constrained discretion over **who** is on a
  watchlist and **where** it is deployed, and a failure in the public sector
  equality duty regarding demographic performance. Check the judgment and the
  ICO's and Biometrics Commissioner's responses.
- **The Met's LFR programme** and its subsequent independent evaluation (the
  National Physical Laboratory study of the Met's and South Wales' LFR
  algorithm's demographic performance is the key technical document, and the
  reason "equitable performance across demographics, measured" is now a tender
  question rather than an ethics slide).
- **Standing operating procedures** that emerged: published deployment criteria,
  watchlist justification, signage, immediate deletion of non-matches, and
  officer-in-the-loop adjudication of every match.

**Generalise the lesson past facial recognition, because your customer will.**
The *Bridges*-shaped questions are now asked of every analytic: *who decided the
threshold and on what basis; what is on the equivalent of a watchlist; what is
the demographic performance and who measured it; what happens to the data on a
non-match; and who reviews the deployment?* **A simulator answers the third of
those better than any other instrument available** — you can generate matched
populations varying skin tone, body shape, gait, mobility aid and clothing, and
report per-stratum performance with real ground truth. R03 §9.3's note about the
`disabled_mobility` catalogue row is exactly this: a fairness test case that
should be mandatory, not optional.

### 5.4 The inquiry layer: what public inquiries concluded about monitoring

This is the richest available evidence about how surveillance actually fails, and
it is all **[VERIFY]** in this session. Treat the findings as accurately
characterised but re-check wording before quoting.

**The Manchester Arena Inquiry (Saunders), Volume 1: *Security for the Arena*
(2021).** The findings relevant to us, as I understand them:

- The bomber conducted **hostile reconnaissance of the City Room in the days
  before the attack and on the evening itself**, spending an extended period in a
  mezzanine area, and was **visible to CCTV and to staff**.
- There was a **CCTV blind spot** covering the area the bomber occupied, and the
  inquiry was critical of both the coverage and the way the system was monitored.
- A member of the public reported concerns about the bomber to a steward; the
  escalation did not result in effective action.
- The inquiry made findings of **missed opportunities** and criticised the
  security arrangements of the venue operator and the contracted security
  provider, and the British Transport Police deployment.

Check the inquiry's own site ([manchesterarenainquiry.org.uk](https://www.manchesterarenainquiry.org.uk/))
and the Volume 1 report.

**Why this is the most important single document for anyone selling behaviour
analytics in the UK. [lore]** It establishes, in a legal forum, all four of the
following at once: (1) **hostile reconnaissance in the target's own camera
coverage is a real and observed phenomenon**, not a marketing scenario; (2)
**camera coverage gaps are decisive**, which makes camera-placement analysis a
life-safety activity rather than an engineering nicety; (3) **the person who
noticed was a member of the public, not the system**, which is a standing rebuke
to any architecture that ignores human-report ingestion; and (4) **detection
without effective escalation is worth nothing**, which is the same finding as
Smith's "vicarious custodians" from §2.5, arriving via twenty-two deaths.

The follow-through is **Martyn's Law — the Terrorism (Protection of Premises)
Act 2025 [VERIFY]** — which imposes duties on qualifying public premises and
events, with a tiered regime (a standard tier based on procedures, and an
enhanced tier for larger capacities with additional measures), overseen by a
regulator and with a phased implementation period. **The commercial significance
is enormous and under-appreciated:** it creates, for the first time, a **legal
duty on tens of thousands of mid-sized UK venues** — venues that have never
bought analytics, have no control room, and have a duty manager rather than a
security manager. **[VERIFY]** the qualifying capacity thresholds and the
implementation date before quoting. **The product implication:** the growth
market created by Martyn's Law is not a 200-camera control room; it is **a
handful of cameras, no dedicated operator, and a requirement to demonstrate
that procedures exist and were followed.** That is a different product — cheap,
self-configuring, evidence-producing, and mostly about *documented procedure*
rather than detection.

**The Euro 2020 final at Wembley and the Baroness Casey Review (2021)**
**[VERIFY]**. The review examined the mass disorder and unticketed entry on
11 July 2021. As I understand its content: it described a near-miss of
potentially fatal proportions, criticised the absence of an accountable
end-to-end risk owner for the event, and found that the scale of the unticketed
crowd build-up outside the stadium was not adequately anticipated or acted upon.
Check [thefa.com](https://www.thefa.com/) for the published review.

**What analytics might genuinely have added at Wembley, stated carefully.** Not
"detecting the attackers". The failure was one of **anticipation and capacity
management** in the approach and concourse zones hours before kickoff: crowd
density, arrival-rate versus processing-rate at each ingress, and pressure
build-up at specific chokepoints. Those are **measurable, physically grounded,
non-behavioural, non-biometric quantities** — and they are precisely what a
crowd simulator plus density estimation can provide. **The honest pitch to an
event customer is capacity and flow, not threat.** It is more defensible,
more measurable, more saleable, and addresses the failure mode the inquiries
actually identified.

### 5.5 Crowd disasters: the strongest case for the least glamorous analytic

Three reference events, all **[VERIFY]**:

- **Hillsborough (1989)** — 97 deaths from crushing in pens 3 and 4. The
  Taylor Report's conclusions transformed UK stadium safety and created the
  regime that the Green Guide now embodies. **The CCTV-specific detail that every
  practitioner in this field should know:** the control room had cameras on the
  pens and the crush was, in some measure, *visible*, yet was interpreted as a
  pitch invasion rather than a crush. **This is not a detection failure. It is an
  interpretation failure under stress with a wrong prior.** No improvement in
  detection recall addresses it. What addresses it is a **quantitative density
  readout that contradicts the wrong prior**: not "something is happening in pen
  3" but "pen 3 is at 9 persons/m² and rising". That distinction — *replacing
  interpretation with measurement* — is the single most defensible value
  proposition for crowd analytics that exists, and it is 36 years old.
- **Itaewon, Seoul, October 2022** — ~159 deaths in a progressive crowd collapse
  in a narrow sloped alley during Halloween crowds, with an unplanned,
  un-managed, un-owned event and documented pre-incident emergency calls
  reporting crush danger that were not acted upon effectively.
  **Lesson:** the deadliest crowd events are increasingly **spontaneous and
  ownerless**, which means the customer for the analytic is a **city**, not a
  venue, and the sensing must work on **existing municipal cameras in narrow,
  sloped, night-time, heavily occluded scenes** — the hardest possible imaging
  conditions and, again, a synthetic-data problem.
- **Astroworld, Houston, November 2021** — 10 deaths in a crowd surge at a
  ticketed festival; the after-action reporting focused on show-stop authority,
  ingress control and the absence of a clear trigger for halting the performance.
  **Lesson:** the missing artefact was not information but a **pre-agreed
  threshold and a named person with authority to act on it.** An analytic that
  produces a number without a pre-agreed threshold and owner produces nothing.

**The synthesis across all three, and it is the thesis of this section. [lore]**
In every major crowd disaster of the last forty years, **someone could see it and
the system did not convert seeing into acting.** The bottleneck is not sensing.
It is (a) turning imagery into a *quantity*, (b) comparing that quantity to a
*pre-agreed threshold*, and (c) routing it to a *named decision-maker with
authority*. A vendor who builds (a) and ignores (b) and (c) has built a better
view of the same disaster. **Density estimation with calibrated thresholds and an
auditable escalation path is a more valuable and more honest product than
behavioural threat detection, and it is defensible in an inquest.**

---

## 6. User group (e): MOD, Dstl and defence users

### 6.1 The users

- **Base and estate protection** — force protection of UK bases and deployed
  locations. Structurally identical to CNI (§3) with a different assurance
  regime and a much greater tolerance for degraded and expeditionary conditions.
- **ISR / FMV analysts** — the people watching full-motion video from airborne
  platforms. The defining characteristic is **volume**: more collected video than
  can possibly be watched, which is the founding premise of every ISR automation
  programme since the mid-2010s.
- **Dstl** — MOD's science and technology arm and the technical authority who
  would assess a system like this ([Dstl](https://www.gov.uk/government/organisations/defence-science-and-technology-laboratory)).
- **DASA** — the SME front door ([DASA](https://www.gov.uk/government/organisations/defence-and-security-accelerator)).
- **Defence AI Centre / Defence Digital** — central AI organisation and the
  digital delivery arm ([DAIC](https://www.gov.uk/government/groups/defence-artificial-intelligence-centre)).
- **Army Warfighting Experiment (AWE)** and **NATO DIANA** — the experimentation
  venues where capability is tried in a field setting rather than a lab
  **[VERIFY]**.

R06 §3 in this directory covers the institutional map in more detail and should
be read alongside this section.

### 6.2 The vocabulary, and the Project Maven precedent

**Project Maven (the US Algorithmic Warfare Cross-Functional Team, from 2017)** is
the canonical reference, and the **analyst-burden framing is the part to
reproduce, because it is the framing your defence customer already uses.**
**[VERIFY] the exact wording** — the much-quoted formulation is that analysts were
spending the majority of their time doing mind-numbingly repetitive object
counting in FMV, and that the programme's purpose was to automate that in order to
free human judgement for analysis. Check the DoD's own 2017 establishment memo and
Bob Work's public statements.

The UK register of the same idea, carried from R06:

> **[X]** MOD's digital/AI direction is expressed as enabling Defence "to sense,
> understand, decide, and act faster than adversaries by fusing intelligence and
> targeting data through AI and machine learning software"
> ([Halldale, DSEI 2025](https://www.halldale.com/defence/dsei-2025-prepared-for-20-40-40)) **[V?]**,
> and the vendor-side register that mirrors it is language about reducing
> "workloads and cognitive burden" to produce "faster, better decisions".

**Dstl's own vocabulary that a candidate should use unprompted [VERIFY] at
[gov.uk/dstl](https://www.gov.uk/government/organisations/defence-science-and-technology-laboratory):**
**"human-machine teaming"** (the explicit framing of the human and the algorithm
as a team with allocated functions, rather than automation replacing a human),
**"reducing analyst cognitive burden"**, **"decision advantage"**,
**"dependable AI"** (and **JSP 936**, the MOD's dependable-AI policy direction —
R06 §3), and **"synthetic environments"**.

**The most important translation in this whole document. [lore]** Defence does not
buy accuracy; it buys **assurance**. R06 §3 puts it exactly right: *"you cannot
assure what you cannot systematically test, and you cannot systematically test a
surveillance model on real footage you are not allowed to collect."* A dependable-AI
policy regime is a **procurement-level demand for exactly the artefact a simulator
produces**: systematic, repeatable, parameter-swept test evidence with known
ground truth, covering conditions that cannot be collected on demand (bad weather,
night, rare behaviours, specific demographics, sensor failures). **Everything a
simulator is bad at — photorealism at the margin — is not on the assurance
critical path. Everything it is uniquely good at is.**

### 6.3 What the defence user asks that nobody else does

1. **What is the SWaP-C?** Size, weight, power and cost — because it is going on a
   mast, a vehicle or an airframe with a fixed budget for all four.
2. **Does it work disconnected?** Denied, degraded, intermittent and
   limited-bandwidth (DDIL) operation is assumed, not exceptional. Cloud inference
   is often simply disqualifying.
3. **What is the assurance evidence and who generated it?** See above.
4. **What is the human-machine function allocation?** Which decisions does the
   machine make, which does it recommend, and which does it merely surface?
5. **What is the export-control and sovereignty position** of the model, the
   weights, and the training data? (R06 §3: a simulator and its synthetic outputs
   are generally far less export-sensitive than trained weights or real ISR
   imagery.)
6. **Can we test it in an AWE or a DIANA-style event, on our terms, on our data?**

---

## 7. User group (f): event and stadium security

### 7.1 Who they are and what governs them

The users are the **safety officer** (a statutory-ish role in UK regulated
sports grounds), the **head of stewarding**, the **event control commander**, the
**local authority safety advisory group (SAG)**, and for large events a **police
commander** operating in parallel. **Critically: the safety officer's duty is
capacity and crowd safety, not crime.** A vendor who walks in talking about
threat detection is talking to the wrong duty.

The governing document in the UK is the **SGSA "Green Guide" — the Guide to
Safety at Sports Grounds**, published by the Sports Grounds Safety Authority
**[VERIFY]** at [sgsa.org.uk](https://sgsa.org.uk/). The features that matter to
an analytics vendor:

- It sets out **capacity calculation** methodology — holding capacity as the
  lesser of entry, exit, and (P)-factor/(S)-factor-adjusted physical capacity —
  which means **the customer already thinks in quantitative density and flow
  terms** and has numbers your product must speak to. **[VERIFY]** the current
  edition's terminology and any published density figures.
- It specifies **CCTV requirements for monitoring the crowd**, and the control
  point arrangements, including the expectation that the safety officer can view
  and communicate with the whole ground.
- It embeds a **counting-and-monitoring obligation** — knowing how many people are
  in each section, in real time.

**That third bullet is the sale.** Automated occupancy counting per sector,
reconciled against turnstile counts, with density and flow readouts and
pre-agreed thresholds, maps **directly onto an existing statutory duty the
customer is already failing to discharge well.** It is also the thing the
Hillsborough, Wembley, Itaewon and Astroworld lessons all converge on (§5.4–5.5).

Alongside it: **UEFA and FIFA stadium and safety/security regulations** (for
clubs in European competition, a separate and binding compliance layer)
**[VERIFY]**; and for counter-terrorism, **ProtectUK** and the CT security
adviser network ([protectuk.police.uk](https://www.protectuk.police.uk/)), plus
Martyn's Law (§5.4).

### 7.2 The drone problem

**[VERIFY]** Counter-UAS is now a standing agenda item for every major venue, and
the honest position is uncomfortable: detection is tractable (RF detection and
Remote ID — see R05 §2.7), **mitigation is legally restricted to state actors in
most jurisdictions**, and therefore what the venue actually buys is
**situational awareness plus a procedure**: know it is there, know where the pilot
probably is, decide whether to hold the show. A vendor should be explicit that
they sell detection into a procedure, not a solution.

### 7.3 What the event customer asks

1. Does it work in our lighting — floodlights, pyrotechnics, strobes, dusk-to-dark
   transition during a fixture?
2. Does it survive the density we actually get — 4+ persons/m² with heavy mutual
   occlusion, where per-person detection fails and only density estimation works?
3. Can it be stood up and struck down for a one-off event, by contractors, in a
   day?
4. What does it cost per event, not per year? (Event security is a **per-event
   opex** buyer, not a capex buyer. This alone eliminates most enterprise
   analytics pricing models.)
5. Does it integrate with our turnstile and ticketing counts, so the numbers
   reconcile?
6. Will it produce something I can hand the SAG and the regulator?

---

## 8. User group (g): retail and corporate — briefly

Covered lightly, per scope, but two features of these users are worth knowing
because they distort the whole market's vocabulary. [lore]

- **Retail loss prevention is the volume market and it sets the price expectation
  everyone else inherits.** Its metrics are shrink, incidents per store,
  and per-store subscription cost; its tolerance for false alarms is high in the
  review queue and near-zero for staff intervention; and its legal exposure runs
  through discrimination and wrongful-detention claims. **The UK retail-facial-
  recognition controversy (Facewatch and the ICO's engagement with it) [VERIFY] is
  the case study**: the reputational and regulatory risk of a false positive that
  results in a customer being refused service is much larger than the loss
  prevented.
- **Corporate GSOCs** (global security operations centres) are the most
  commercially sophisticated buyers and the most technically permissive — cloud is
  acceptable, integration budgets exist, and they will genuinely run a structured
  pilot. They are where the false-alarm-filtering vendors in R03 §5.3 make their
  money. Their requirement that is rare elsewhere: **global, multi-site,
  multi-jurisdiction deployment**, which makes per-jurisdiction configuration of
  what is even legal to detect (works-council and employee-monitoring constraints
  in Germany and France, for instance) a hard product requirement.

---

## 9. Synthesised requirements table

Every row is traced to the user group and evidence that generated it. "Source
strength" uses the marks from §0. **F** = functional, **NF** = non-functional.

### 9.1 Functional requirements

| # | Requirement | Driving user | Evidence | Strength |
|---|---|---|---|---|
| F1 | Alarm output must be **event-level and de-duplicated**: one real event = one alarm, with latency counted as part of correctness | All | i-LIDS 10-second scoring rule ([R03 §2.3](./R03_behaviour_intent_anomaly_detection.md)) | [X] |
| F2 | Every alarm must carry **pre-roll and post-roll video** (order 10 s each), bounding box, and zone/track history | CCTV ops, CNI | NPSA verification requirement; R03 §5.4 | [X] |
| F3 | Alarm must be expressible as **observables** ("dwell 240 s, 4th visit in 9 days, oriented at loading bay"), never as an inferred mental state | Police, CNI | Servator "negate or confirm"; GAO SPOT 54% | [X] |
| F4 | **Camera health and integrity** detection (tamper, defocus, occlusion, signal loss, PTZ home drift, scene change) as a first-class alarm class distinct from security alarms | CNI, border | R05 §1.3 sustainment finding; §3.4 R5 | [lore]+[X] |
| F5 | **Density and flow estimation** with calibrated per-zone thresholds and reconciliation against turnstile/entry counts | Event, police, city | Green Guide capacity duty; Hillsborough/Itaewon/Astroworld | [VERIFY]+[lore] |
| F6 | **Retrospective search** by event type and person/vehicle descriptive attributes across archived footage | Police investigators | West Yorkshire Police tender wording | [Q] |
| F7 | **Automated redaction** for disclosure | Police | Sussex PCC tender | [Q] |
| F8 | **Cross-camera, cross-day identity persistence** sufficient to support revisit counting without claiming biometric identification | Police CT, CNI | Hostile-recon corroboration argument, R03 §4.3 base-rate arithmetic | [X] |
| F9 | **Multi-tenant configuration and per-tenant audit** in a shared control room | CCTV ops | Westminster→H&F; Thames Valley partnership; EUROSUR multi-authority | [Q] |
| F10 | **Human-report ingestion**: a steward's or member of the public's report must be able to enter the same picture as a sensor detection | Event, police | Manchester Arena: the person who noticed was a member of the public | [VERIFY] |
| F11 | **Escalation routing with named owner and pre-agreed threshold**, not just alarm generation | All | Astroworld show-stop authority; Smith's "vicarious custodians" | [Q]+[VERIFY] |
| F12 | **Configuration audit trail**: every deviation from shipped defaults logged, attributed and visible to the manager | CCTV ops, CNI | Keval & Sasse "poor configuration of technology" | [Q] |
| F13 | **Shadow / non-operational mode** producing no operational decisions, for regulated pilots | CCTV ops (LA), police | SCCoP: seek advice before any trial in a public place | [Q] |
| F14 | **Person counting under severe degradation** (long range, oblique, haze, sea state, night) with an uncertainty estimate | Border | Channel safety-of-life counting task | [lore] |
| F15 | **Per-stratum performance reporting** across skin tone, body shape, gait, mobility aids and clothing | Police, all regulated | *Bridges* / PSED; NPL LFR demographic study; R03 §9.3 | [VERIFY] |
| F16 | **Export in the customer's schema** — ONVIF events, VMS/PSIM integration, C2 geo-referenced tracks | All | Keval & Sasse "lack of system integration"; EUROSUR geo-referencing | [Q]+[X] |

### 9.2 Non-functional requirements

| # | Requirement | Driving user | Evidence | Strength |
|---|---|---|---|---|
| NF1 | **Alarm budget: single-digit actionable alarms per operator-shift across the whole estate** | CCTV ops | 200 cameras / ~1 operator on shift (§2.1) × "3–4 false alarms destroys trust" (R03 §5.2) | [Q]+[X] |
| NF2 | **Nuisance-alarm rate evidenced by a 30-day on-site logged trial**, broken out by zone and hour, with the weather record | CNI | R05 §1.6 | [X] |
| NF3 | **On-premises inference with no egress**, configurable to zero external connectivity | CNI, defence | Security-minded approach; DDIL operation | [lore] |
| NF4 | **CAPSS-assurable and CSE-listable**, or a credible roadmap to it | CNI (UK) | NPSA CAPSS wording | [X] |
| NF5 | **Operable by a person with ~31 hours of formal training**, on night shift, without vendor support | CCTV ops | SIA licensing figures | [Q] |
| NF6 | **Calibrated confidence** (reliability diagrams, ECE) because displayed confidence modulates operator reliance | All | Applied Ergonomics 2012 via R03 §5.5 | [X] |
| NF7 | **Works at the customer's real bitrate, codec, resolution and frame rate**, not the demo's | CCTV ops | Keval & Sasse "poor quality video recordings"; [R04](./R04_degraded_imaging_and_sim2real.md) | [Q] |
| NF8 | **DPIA-ready documentation pack** shipped as a product artefact | All UK civil | ICO video-surveillance guidance (R03 §9.2) | [X] |
| NF9 | **Purpose-bounded**: the deployed configuration must be constrained to the authorised purpose and demonstrably so | CCTV ops (LA) | SCCoP Principle 1 "specified purpose… pressing need" | [X] |
| NF10 | **SWaP-C envelope stated**, and disconnected operation demonstrated | Defence | §6.3 | [lore] |
| NF11 | **Availability and maintenance economics quantified**: MTBF, re-calibration interval, cost per camera per year | Border, CNI | GAO/EFF tower sustainment record | [X] |
| NF12 | **Effectiveness-measurement instrumentation built in**: baselines, cue-to-outcome attribution, availability accounting | Border, all public-sector | GAO's standing critique of CBP metrics | [VERIFY] |
| NF13 | **No emotion/deception inference anywhere in the product or its marketing** | All EU/UK | EU AI Act Art. 5 prohibitions (R03 §9.3); GAO SPOT | [X] |
| NF14 | **Per-jurisdiction feature gating** (what may legally be detected differs by country and by workplace-consultation regime) | Corporate | §8 | [lore] |
| NF15 | **Priced per event / per site / per seat in ways that match the buyer's budget line** — opex for events, capex-with-Safer-Streets-timing for councils | Event, CCTV ops | §2.3, §7.3 | [lore] |
| NF16 | **Stable across versions**: a model update must not silently change the operating point the customer tuned to | All | [lore] — the most common cause of pilot-to-production regression |

**The single most important line in the two tables is NF1**, and it should be
computed for the specific customer in front of you, on a whiteboard, in the first
meeting. It converts an abstract argument about false alarms into an arithmetic
constraint the customer recognises as their own life. Doing that arithmetic
unprompted is the highest-credibility act available in this market. [lore]

---

## 10. What they actually ask vendors in pilots: twenty questions

Assembled from the doctrine, tenders, PIRs and inquiry findings above. [lore] on
the ordering and phrasing; the substance is traceable to the sections cited.

1. **"Which of my cameras will this not work on?"** — The test of honesty. Every
   estate has a third of its cameras at wrong height, wrong angle, wrong
   resolution or facing a sunrise. A vendor who says "all of them" has failed.
2. **"How many alarms per shift?"** — Not accuracy. See NF1.
3. **"Show me it on my footage, from last Tuesday, that I choose."** — The
   universal demo-killer. Prepare for it.
4. **"What happens at 03:00 in the rain?"** — And in fog, and with wet tarmac
   reflecting sodium lighting, and with a spider on the dome. (R04.)
5. **"Who tuned it, and what happens when they leave?"**
6. **"What does my operator have to do differently?"** — If the answer involves
   new screens, new procedures and new vigilance, the answer is no.
7. **"Does it integrate with [their VMS] — natively, or through a box?"**
   (Milestone, Genetec, Avigilon, Bosch, Axis, Hanwha, Verkada.)
8. **"Is it in the Catalogue of Security Equipment / is it CAPSS assured / has it
   passed i-LIDS?"** — CNI and government. §3.2.
9. **"Where does the video go?"** — Egress, retention, sub-processors,
   jurisdiction.
10. **"Can you give me a DPIA and an equality-impact position?"** — Increasingly
    asked before, not after. §2.2, NF8.
11. **"What is the demographic performance and who measured it?"** — Post-*Bridges*.
    §5.3, F15.
12. **"What is the false-negative behaviour?"** — i.e. when it misses, does it
    miss silently? Managers fear silent misses more than false alarms, because a
    false alarm is visible and a miss appears in an inquiry.
13. **"Can we run it in shadow mode first, with no operational effect?"** — F13.
14. **"How is it licensed, and what happens to my data if you are acquired or go
    bust?"** — Exit and escrow. Small-vendor risk is a real procurement blocker.
15. **"Who is liable if we act on it and are wrong?"** — And its shadow: who is
    liable if we *don't* act because it didn't alarm.
16. **"What is the total cost including integration, cameras we'll have to move,
    and the network we'll have to upgrade?"** — Analytics projects routinely fail
    on the third item.
17. **"Can I turn individual detections off per camera, per time of day, per
    tenant?"** — F9, NF9.
18. **"Show me your pilot exit criteria, agreed in advance and in writing."** —
    The most sophisticated customers insist; see §11.
19. **"What will you measure availability against?"** — NF11. Uptime, not just
    accuracy.
20. **"What do your existing customers in my sector say — and can I ring one?"** —
    Reference-ability in a small, closed, heavily-cleared community is the real
    barrier to entry, not technology. [lore]

---

## 11. Why pilots fail

Six mechanisms, each anchored to documented cases.

### 11.1 No agreed success criteria (the dominant cause)

**The pattern:** a pilot runs, produces some alarms, and everybody has a different
recollection of what would have counted as success. The vendor cites detections;
the customer cites nuisance; nobody has a baseline. It ends in "interesting, no
budget".

**The documented analogue is GAO on TSA SPOT and on CBP towers.** **[X]** *"10
years after the development of the SPOT program, TSA cannot demonstrate the
effectiveness of its behavior detection activities"* — after **$900 million** and
3,000 officers ([GAO-14-158T](https://gao.gov/products/GAO-14-158T),
[GAO-14-159](https://www.gao.gov/products/gao-14-159)). The same criticism recurs
against CBP's technology programmes **[VERIFY]**. If a federal programme running
for a decade at that scale cannot demonstrate effectiveness, a twelve-week vendor
pilot certainly cannot unless success was defined on day one. **Fix: write the
exit criteria, the baseline measurement period, and the metric definitions into
the pilot agreement before a camera is touched.**

### 11.2 The demo-to-site gap

**The pattern:** performance measured in a vendor lab or on a curated clip
collapses on the customer's estate. Keval & Sasse named the two proximate causes
**[Q]**: *"poor configuration of technology"* and *"poor quality video
recordings"*. R04 in this directory is entirely about the imaging side of this
gap. **Fix:** a pre-pilot **site survey with recorded sample footage from the
worst cameras**, scored before commercial commitment. A vendor who insists on
this wins trust even when the answer is partly negative.

### 11.3 Integration was assumed to be someone else's job

**The pattern:** the analytic works, and the alarm cannot reach the operator's
existing screen, so the pilot ends with a second monitor nobody watches. Keval &
Sasse: **[Q]** *"a lack of system integration"*. This is also the recurring border
finding: a new sensor whose picture does not merge with the old one means
operators run two systems and use the one they trust. **Fix:** treat VMS/PSIM/C2
integration as the first deliverable, not the last.

### 11.4 The evaluation was of the wrong thing entirely

**The pattern:** everyone measures detection quality, while outcome variance is
actually driven by siting, staffing and process. **The canonical documented case
is the Home Office's own CCTV evaluation** — Gill & Spriggs, HORS 292 (2005),
whose retrievable framing is **[Q]** *"While CCTV can be a powerful tool in
combating crime, the contexts in which CCTV systems operate are very variable, as
are the systems themselves"*, across 13 of 684 projects
([HORS 292](https://popcenter.asu.edu/sites/g/files/litvpz3631/files/Responses/video_surveillance/PDFs/Gill&Spriggs_2005.pdf)).
**[VERIFY]** the widely-quoted "only one of thirteen systems showed a significant
reduction" claim before using it.

**The lesson, and it is the reason a simulator is a commercial instrument and not
just an engineering one:** the variables that determined the outcome of a £170m
national CCTV programme — camera placement, coverage, lighting, staffing ratio,
escalation process — are **exactly the variables a simulator can sweep and a real
pilot cannot.** You cannot re-site a customer's cameras four ways to see which is
best. You can do it four hundred ways in a simulator.

### 11.5 Sustainment was never costed

**The pattern:** year one works, year three doesn't, because nobody funded
cleaning, re-calibration, spares or model maintenance. **The documented case is
the US border towers:** **[X]** the EFF's summary of two decades of audit is
*"U.S. Border Surveillance Towers Have Always Been Broken"*
([EFF](https://www.eff.org/deeplinks/2024/10/us-border-surveillance-towers-have-always-been-broken)),
and R05 §1.3's reading stands: the dominant failure mode is *"uptime, power,
comms, calibration drift, and maintenance economics"*, not classifier recall.
**Fix:** quote a per-camera-per-year sustainment figure and a re-calibration
interval, unprompted. NF11.

### 11.6 Regulatory or industrial-relations collapse

**The pattern:** the pilot is stopped not by performance but by a DPIA that was
never done, a regulator's intervention, a union grievance, or a press story.
Recall the retrieved SCCoP text **[Q]**: authorities "are encouraged to seek
advice from the Commissioner and other regulators **before any trial or pilot of
new technology is undertaken in a public place**". **[VERIFY]** the UK
retail-facial-recognition (Facewatch) regulatory engagement and the *Bridges*
judgment as the two best-documented cases of a deployment stopped or constrained
on legal grounds rather than technical ones. **Fix:** ship the DPIA template and
the shadow-mode configuration as product, and never be the reason a named officer
gets a regulator's letter.

---

## 12. What these users actually think about AI

Assembled from the doctrine and the ethnography; **[lore]** on synthesis,
sourced where marked.

**They have been sold "intelligent video" before, and it didn't work.** Anyone in
this field over forty lived through the mid-2000s analytics wave — motion-based
"intelligent" VCA that alarmed on rain — and the institutional memory is
visceral. **Your first job is not to demonstrate capability; it is to distinguish
yourself from the last three vendors.** The fastest way to do that is to name the
failure modes before the customer does (rain, headlights, foliage, spiders,
shadows, wet tarmac) and show what yours does on each.

**Trust is asymmetric and cheap to destroy.** R03 §5.2: **[X]** *"Research shows
that after three or four false alarms, operators begin to distrust the system"*
([Actuate](https://actuate.ai/alarm-fatigue/)). Once distrusted, a system is not
merely ignored — it is **actively worked around**, and the operator's workaround
becomes invisible to management. This is the real reason deployed analytics
"stops working" without any technical change.

**They want explanation as evidence, not as interpretability.** R03 §5.5 states
it correctly: explainability here is *"show me the evidence in three seconds"*.
No operator wants a saliency map. They want the clip, the box, the track, and one
line of why. **The test: can the operator, in three seconds, decide to escalate or
dismiss, and defend that decision later?**

**Accountability is their personal exposure, not an abstraction.** The control-room
supervisor, the safety officer and the CNI security manager are all individuals
who can be named in an inquiry (§5.4) or an inspection finding. This produces a
specific and rational preference that vendors consistently misread as
conservatism: **they would rather have a system that misses and says nothing than
a system that alarms confidently and wrongly**, because the second one puts their
name on a decision. Which means: **under-claim, expose uncertainty, and never
auto-act.** R03 §5.4's rule — *"never auto-dispatch on a behaviour analytic"* — is
not caution, it is what the customer wants.

**Industrial relations are a real and under-modelled blocker. [VERIFY]** In UK
local government and transport, control-room staff are unionised (UNISON, GMB,
RMT and ASLEF in rail contexts), and a system presented as *"the AI watches the
cameras"* triggers a straightforward job-security dispute, plus a legitimate
challenge about performance monitoring of staff. Note that the same video
infrastructure can monitor employees, and the EU AI Act's workplace
emotion-recognition prohibition lands squarely here (a staffed control room is a
workplace — R03 §9.3). **The framing that survives a union conversation is
"the system watches the empty perimeter at 4am so the operator can watch the
high street", i.e. augmentation of coverage the human cannot provide, plus an
explicit written commitment that outputs will not be used for staff performance
management.** Get that commitment into the pilot agreement; it costs nothing and
removes the most likely non-technical blocker.

**The ICO and the regulators are consulted earlier than vendors expect.** R03 §9.2:
**[X]** organisations *"must take a data protection by design and default approach
and perform a Data Protection Impact Assessment (DPIA) for any processing that is
likely to result in a high risk"*
([ICO](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/cctv-and-video-surveillance/)),
with audio and biometric identification as the two flags. Combined with the SCCoP
pilot advice **[Q]** and the *Bridges*-shaped questions in §5.3, the practical
reality is that **a UK public-sector customer's compliance officer is in the room
by meeting two.** Arrive with the paperwork.

**Where they are genuinely enthusiastic.** Three areas, consistently, and all
unglamorous: **retrospective search** ("find me the man in the red jacket across
nine hours and six cameras" — days of work to minutes, and it is what they are
actually buying, §2.3); **redaction and disclosure** (pure workload relief, no
civil-liberties downside, statutory driver); and **camera health** (they know a
third of their estate is degraded and cannot prove which third). **A vendor whose
first three modules are search, redaction and health will be believed when it
later proposes behaviour analytics. A vendor whose first module is threat
detection will not.** [lore]

---

## 13. How these users would actually use a simulator

Five uses, each with a precedent that makes it credible to a procurement officer.
This section is the commercial case for this repository, expressed in the
customer's language rather than the developer's.

### 13.1 Acceptance testing and procurement benchmarking

**The use:** the customer defines a scripted corpus of scenarios — sterile-zone
intrusion in four weather states, abandoned bag on a crowded platform, a
loitering-then-tampering sequence, a counter-flow at an exit — and requires every
bidding vendor to be scored on it, identically, with known ground truth, before
anyone touches the live estate.

**The precedent that makes this saleable is i-LIDS itself**, and the argument is
almost too neat. **[X]** i-LIDS exists because government needed *"to facilitate
development and selection of video analytics to meet Government requirements for
security operations"*, and its corpus design is *"approximately 24 hours of
footage… filmed to represent all weather conditions, time of day and scene
densities expected within the scenario… two or three camera views"*
([i-LIDS standard paper](https://www.researchgate.net/publication/284353547_Imagery_Library_for_Intelligent_Detection_Systems_i-LIDS_A_Standard_for_Testing_Video_Based_Detection_Systems)).
R03 §2.2's observation is the entire pitch: **that corpus took a government
science establishment years and a film crew to build, it covers five scenarios [audit 2026-09-26: was "four"],
access is controlled, and it cannot be extended to a customer's specific site.
A simulator can generate an i-LIDS-shaped corpus — 24 hours, all weather, all
times, multi-view, with deliberate non-alarm events — for an arbitrary scenario,
on demand, for a specific site geometry.** That is not a research contribution
dressed as a product; it is a procurement instrument.

Related precedent: **NIST ActEV / DIVA / MEVA** (R03 §2.4) as the US model of
sequestered-data, rate-based scoring — and the fact that its data is sequestered
is precisely why an openly shareable synthetic equivalent has value.

### 13.2 Camera placement and coverage design

**The use:** before buying cameras, sweep placements, heights, lens choices and
PTZ presets against the detection task and the site's real geometry, and produce
a coverage argument — including **where the blind spots will be and what will not
be seen from anywhere.**

**The precedent is the Manchester Arena Inquiry (§5.4) [VERIFY]**, which found a
CCTV blind spot in the area where hostile reconnaissance occurred. Once a public
inquiry has established that coverage gaps are a life-safety matter, **"we
modelled the coverage and here is the residual blind-spot map, signed and dated"**
becomes a due-diligence artefact for the security manager and their insurer, not
a technical nicety. Martyn's Law duty-holders (§5.4) need exactly this and have no
means of producing it.

This is also the direct answer to the Gill & Spriggs finding (§11.4): if siting
dominates outcomes, then siting is what should be optimised, and simulation is the
only affordable way to optimise it.

### 13.3 Operator training and competency assurance

**The use:** generate scripted incident scenarios of graded difficulty with known
ground truth, and use them to (a) train operators, (b) assess competency
repeatably, and (c) provide the competence evidence a PSeMS-style management
system requires (§3.2).

**The precedents are twofold.** First, **synthetic-environment training is
established and funded in UK defence**: Dstl and MOD synthetic environments, and
the commercial simulation lineage (**Bohemia Interactive Simulations' VBS**
family, used widely for military training **[VERIFY]** at
[bohemia.com](https://bisimulations.com/)) mean the concept needs no defending in
a defence or CT room. Second, the user-side driver from §2.1: operators enter the
role with **~31 hours of formal training [Q]**, and the industry has no repeatable
way to assess control-room competency on rare events, because rare events are
rare. **A generator of rare events is a competency-assessment instrument** — and
it is arguably a bigger and less contested market than the analytics itself,
because it has no data-protection exposure at all. [lore]

Note the second-order benefit that the vigilance literature implies (R03 §5.1):
because self-report is not a control on vigilance decrement, an organisation needs
**injected verification tasks** to measure operator state. A simulator that can
inject a synthetic-but-realistic event into a live-looking feed is the mechanism
for that. Handle the ethics and the union position explicitly (§12) before
proposing it.

### 13.4 Red-teaming and adversarial assessment

**The use:** ask what an adversary does to defeat the system, and generate it —
approach routes that exploit camera geometry, movement that stays below dwell
thresholds, clothing changes between non-overlapping views to break re-ID, use of
crowd occlusion, standoff positions outside the fence line (§3.3, Moore County),
and the deliberately-benign behaviours that produce the same signature as an
attack.

**The precedents:** NPSA's own doctrine is adversary-centred — **[X]** detection
depends on *"understanding where hostiles might conduct their reconnaissance
from"* ([NPSA](https://www.npsa.gov.uk/specialised-guidance/hostile-reconnaissance/disrupting-hostile-reconnaissance)) —
and NPSA/CAST **test facilities and evaluation schemes** exist precisely to
subject products to adversarial trial rather than vendor demonstration (§3.2,
R05 §1.2).

**The technical hook to this repository:** R03 §7.1 notes that the differentiators
of this simulator include **explicit hard negatives tagged `hard_negative_for`**.
That field *is* a red-team artefact. A red-team exercise's output is a set of
behaviours that produce the wrong answer, and a simulator is the only place those
can be catalogued, versioned, and re-run against every future model release.
**Regression-testing against a growing library of adversary behaviours is
something no real-footage programme can do**, because you cannot ask a real
adversary to repeat themselves.

### 13.5 Effectiveness measurement and assurance evidence

**The use:** produce the numbers the customer's auditor, regulator or inquiry
will ask for — detection rate versus nuisance rate curves per condition, per
demographic stratum, per camera geometry, per weather state, with known truth and
a repeatable protocol.

**The precedents:** GAO's standing finding that CBP could not demonstrate
effectiveness (§4.3, **[VERIFY]**); MOD's dependable-AI policy direction and
JSP 936 (§6.2, R06 §3) and the resulting demand for systematic test evidence; and
the EU AI Act's high-risk obligations, which R03 §9.3 correctly reads as
*"satisfied with test evidence"* — *"Annex-III-style robustness evidence across
weather/lighting/demographics is exactly what synthetic data can produce."*

**The summary argument, and the one to lead with in any government room. [lore]**
Three separate regimes — UK defence dependability policy, EU AI Act conformity
obligations, and public-audit effectiveness requirements — have independently
arrived at a demand for **systematic, repeatable, condition-stratified test
evidence with known ground truth.** Real operational footage cannot supply it:
it has no ground truth, cannot be shared, cannot be stratified on demand, and
cannot contain the rare events that matter. **Synthetic evaluation data is not a
substitute for real data in this argument. It is the only thing that satisfies the
requirement at all.**

---

## 14. Eight personas

Each with a day in the life and the top five pains. All personas are composites;
names are invented. **[lore]** throughout, grounded in the sections cited.

### Persona 1 — Donna, CCTV Control Room Supervisor, shared borough control centre

**Context (§2.1).** 47, eleven years in the room, SIA PSS licensed, £19/hour plus
shift allowance. Supervises a team of five covering 24/7 for two boroughs,
~400 cameras total. Reports to a community-safety manager who reports to a
cabinet member.

**Day in the life.** 06:00 handover, reads the night log. Two ASB reports needing
footage export for the housing team, one police footage request with a deadline, a
request from the licensing team about a specific premises. 09:00 the new audio
noise-detection alerts start firing — refuse lorries, a busker, a road drill —
she mutes the zone and makes a note to raise it. 11:00 a shoplifting call from the
radio-link scheme; she finds the subject, follows him three cameras, loses him at
the underpass where there is no coverage, and tells the officer where he was last
seen. 13:00 an hour of footage review for a disclosure request. 15:00 a
distressing incident: a man on a bridge; she stays on him for fifty minutes while
negotiators arrive, and then goes back to the ASB exports. 17:00 she writes up the
day, notes the audio false alarms again, and hands over.

**Top five pains.** 1. The footage-request queue is unbounded and is her real job,
not watching. 2. The new AI alerts fire on nothing and she has no way to fix it
without ringing the integrator. 3. When she reports something, she rarely learns
what happened, and often nothing did. 4. She has no coverage at the three places
where things actually happen. 5. Nobody has ever asked her what she needs, and
two systems have been installed over her head.

### Persona 2 — Ray, Head of Security, water utility (multi-site CNI)

**Context (§3).** 58, ex-Army, responsible for 200+ unmanned sites and two staffed
works. Budget approved annually against a security plan; audited.

**Day in the life.** Starts with the overnight alarm report: 61 perimeter
activations, all environmental or wildlife, none verified as intrusion, four
cameras offline for over a week. Chases the maintainer on the offline cameras.
A morning meeting on regulatory return evidence — he needs to show alarm
verification times and cannot, because the log does not record when an operator
looked. Afternoon at a remote site with a contractor discussing a fence
replacement; he takes photographs of vegetation growing through the detection
zone. Late in the day, a board request triggered by press coverage of
infrastructure vulnerability: *"are we exposed the way that airport was?"* and he
has no way to answer at portfolio level.

**Top five pains.** 1. Sixty nuisance alarms a night have made the PIDS
functionally decorative. 2. He cannot prove verification happened. 3. He does not
know which of his cameras are actually working today. 4. Sustainment funding is
always the first thing cut. 5. Every new technology proposal creates an assurance
problem (CAPSS, CSE, network exposure) that costs him more effort than the
capability is worth.

### Persona 3 — Sgt. Aisha Rahman, force CCTV hub and Servator liaison

**Context (§5.1–5.2).** 34, ten years' service, runs the interface between the
force control room, three local-authority CCTV estates and CT protective
security. Trained in Servator behavioural observation.

**Day in the life.** Morning tasking: three hotspot locations from the weekly
intelligence product, passed to the council rooms as watch requests. Mid-morning
she reviews four reported "suspicious behaviour" submissions from venue security —
two are photography of a building by someone who turns out to be an architecture
student, one is a genuine repeat-visit pattern worth a Servator deployment, one is
unreadable because the footage is 4CIF and 4fps. Afternoon: she supports a
Servator deployment, and the officers' engagement negates suspicion in six of
seven cases, which is the doctrine working. Evening: a request from a vendor for a
meeting about "AI behavioural threat detection", which she forwards to the
force's data-protection officer and privately expects to be a waste of time.

**Top five pains.** 1. The signal-to-noise ratio of human "suspicious behaviour"
reports is dreadful and they all still need reviewing. 2. Footage quality defeats
half of them. 3. She cannot link the same person across days and estates, which
is the one thing that would make hostile-recon corroboration possible. 4. Every
vendor pitches emotion and intent, which she knows is indefensible. 5. Whatever
she deploys, she must be able to explain in a witness statement.

### Persona 4 — Marek, Border maritime watchkeeper

**Context (§4.1–4.2).** 41, ex-Navy, twelve-hour shifts in a maritime operations
room. Radar, AIS, EO/IR from a UAS feed, VHF, and four screens of other people's
systems.

**Day in the life.** 04:00, weather window opens; he expects activity. A radar
contact with no AIS, 14 nm out, closing. Slews the EO/IR; at that range in haze
he has a smudge. Over forty minutes it resolves into an overloaded RHIB and his
next task is the one that matters most and is hardest: **how many people are on
it**, because that determines the response. He counts 41; the actual number turns
out to be 53. Asset tasked, safe recovery, paperwork. Then three more contacts,
two of which are fishing vessels he wastes twenty minutes on. He logs everything
because the log will be read by lawyers.

**Top five pains.** 1. Counting people at range in bad conditions, when the count
is a safety-of-life decision. 2. Track continuity across sensor handovers — the
same boat appears as three contacts. 3. Distinguishing legitimate traffic, which
is most of what he looks at. 4. Four systems, four pictures, no fusion. 5. Every
action is legally scrutinised and the evidence chain is manual.

### Persona 5 — Claire, Stadium Safety Officer, 32,000-capacity ground

**Context (§7).** 52, twenty years in stewarding and safety, holds the ground
safety certificate responsibility on match days, answerable to the local
authority SAG and the SGSA regime.

**Day in the life (match day).** 09:00 stadium walk with the structural and
fire checks. 11:00 briefing of 380 stewards, half of them casual staff, a third
new this season. 13:00 into event control: eight monitors, turnstile count
feed, radio nets. Turnstiles open; she watches arrival rates, which are 20%
behind where they should be because of a rail issue, meaning a late crush at two
turnstile banks. She holds a gate, opens a reserve bank, and reconciles counts by
hand. Kick-off. Second half, a section with a persistent standing problem and a
smoke device. Post-match egress — her highest-risk twenty minutes — she manages
a staggered release, then writes the report for the SAG.

**Top five pains.** 1. She knows her sector occupancies only approximately and
late. 2. Arrival-rate surprises from outside the ground, which she cannot see. 3.
Casual stewards with minimal training as her primary sensor. 4. Egress crowding
she manages on instinct. 5. Everything must be defensible to the SAG, and she has
a clipboard.

### Persona 6 — Tom, ISR / FMV analyst, defence

**Context (§6).** 29, uniformed, three years on the job, works in shifts on
airborne video with a mission-crew headset and a chat client.

**Day in the life.** Four-hour vulcan: stare at a compound, log every vehicle and
every person in and out, annotate, report. Two hours of it is nothing happening,
which is when he misses things. The mission changes mid-flight; the target moves
and he must maintain track through a treeline and across a road junction where
three similar vehicles converge. He writes the product; the analytical value of
his shift is four sentences that took nine hours to earn. He knows the
"AI will help" brief and his private test is whether it can hold track through
the treeline, because that is where he loses it.

**Top five pains.** 1. Volume — more collected video than can be watched. 2.
Sustained attention on nothing, punctuated by moments that matter. 3. Track
handover and re-acquisition. 4. Tools that are demonstrated in good weather at
good resolution. 5. Nobody asked him to specify what "help" means.

### Persona 7 — Priya, Corporate GSOC Manager, global manufacturer

**Context (§8).** 38, MSc, manages an outsourced 24/7 GSOC covering 140 sites in
26 countries, plus travel-risk and incident management.

**Day in the life.** Overnight report: 2,400 alarms, 2,380 auto-cleared by the
filtering layer, 20 reviewed, 3 escalated, 1 real (a propped door at a plant in
Mexico). Morning call with the outsourced provider on handling times and an SLA
miss. A works-council question from Germany about whether the new analytics
constitutes employee monitoring — she pauses the rollout in two countries.
Afternoon: a vendor QBR where she asks for the per-site false-alarm breakdown and
gets a global average, which she rejects. Evening: budget modelling for next year,
where her argument is cost-per-site-per-month, not accuracy.

**Top five pains.** 1. Per-site variance hidden behind global averages. 2.
Jurisdictional differences in what is legal to detect. 3. The outsourced
operators' turnover destroys accumulated site knowledge. 4. Integration debt
across six VMS platforms. 5. Proving the programme's value to a CFO.

### Persona 8 — Graham, Duty Manager, 900-capacity music venue (the Martyn's Law persona)

**Context (§5.4).** 31, runs the venue's operations. Not a security professional.
Newly a duty-holder under the Terrorism (Protection of Premises) Act regime
**[VERIFY]**.

**Day in the life.** Ordering stock, a staff rota problem, a sound-check
overrunning, and — new this year — a requirement to have and evidence procedures
for evacuation, invacuation, lockdown and communication, and to have trained
staff on them. He has six cameras, a DVR in a cupboard nobody can log into, and
no control room. He has been emailed by four vendors selling AI; he wants to know
the cheapest thing that discharges the duty and does not break on a busy Friday.

**Top five pains.** 1. He does not know what compliance looks like. 2. No budget
and no security staff. 3. His existing CCTV is unusable and he cannot tell. 4.
He cannot evidence that procedures were followed. 5. Everything marketed to him
is designed for someone a hundred times his size.

**Why Graham matters more than his budget suggests.** There are tens of thousands
of him, he has a statutory duty and a compliance deadline, and no product exists
that fits him. A cheap, self-configuring, evidence-producing box that verifies
camera health, counts occupancy against capacity, and logs that a procedure was
exercised would discharge most of his duty. **That is the largest new addressable
market in UK physical security, and it is not a behaviour-analytics product.** [lore]

---

## 15. Twenty questions to ask these users

For a user-research programme. Ordered to build rapport before probing failure.

1. Walk me through your last shift, hour by hour. What did you actually spend time
   on?
2. What proportion of your time is live monitoring versus retrospective work
   (exports, requests, disclosure)?
3. How many alarms did you get last night, and how many mattered?
4. Which of your cameras do you not trust, and how do you know?
5. When you see something, what happens next — precisely, who do you tell, and
   how often do you learn the outcome?
6. What is the last thing you missed that you wish you hadn't? What would have
   had to be different?
7. Which places or times have no coverage, and does anyone senior know?
8. Tell me about a technology that was installed and then not used. Why?
9. What have you turned off, muted or worked around, and why?
10. What would you have to stop doing to use something new?
11. How were you trained, and how do you know you are still good at this?
12. What does your manager get measured on? What do you get measured on?
13. Which document does your organisation get audited or inspected against, and
    what does it say about cameras?
14. What did your last DPIA or equality assessment say, and who wrote it?
15. If you could see one number on a screen that you cannot see today, what would
    it be?
16. What do you tell a new starter that isn't in the training?
17. What has a vendor promised you that turned out to be untrue?
18. What would make you personally unwilling to rely on an automated alert?
19. Who would object if we deployed this — union, legal, comms, the public — and
    what would they say?
20. If this worked perfectly, what would change about your job? Is that a change
    you want?

**Question 20 is the one that decides the project.** [lore] If the honest answer
is "my job gets more scrutinised" or "there'd be fewer of us", you have an
adoption problem that no amount of accuracy fixes, and you need to know it in
week one, not month nine.

---

## 16. Appendix A — the hop chain, with dead ends

Recorded honestly, including what the budget prevented, so the next person can
resume rather than restart.

### A.1 Chain executed for group (a), public-space CCTV — the deepest chain

| Hop | Target | Result |
|---|---|---|
| 1 | Who operates UK public-space CCTV, at what scale and pay | **Succeeded.** Westminster: 100→200 cameras, monitored from Hammersmith & Fulham, £150k, **five operator FTE + one manager**. SIA: £204 licence, ~31 h learning / 22 contact hours, £15–20/hr. **Corrected the brief's "~5,000-camera Westminster" claim.** |
| 2 | The doctrine: Surveillance Camera Code of Practice | **Succeeded.** 12 principles, PoFA 2012, laid 16 Nov 2021, in force 12 Jan 2022, s33(5) duty on local authorities, and the pilot-advice sentence that reframes the whole commercial approach. |
| 3 | Tenders: what councils and police actually buy | **Succeeded.** Kent CC bundled CCTV/access; Sussex PCC automated redaction with demos and user testing as procurement stages; West Yorkshire Police "searchable by events and descriptive factors, minimum 5 users"; NDAA compliance as baseline. |
| 4 | Post-implementation review: Home Office CCTV evaluation | **Partially succeeded.** HORS 292 identified and framing quote obtained; **the PDF host is egress-blocked, so the "one of thirteen" figure could not be verified and is flagged.** |
| 5 | Academic ethnographies | **Partially succeeded.** Norris & Armstrong (888 surveillances, 711 demographically coded, "massively disproportionate targeting"); Smith's *Opening the Black Box* (scanning for "disorderly vistas", "seductive and traumatic", "vicarious custodians"); **Keval & Sasse's five-item failure list — the most valuable single retrieval of the session.** All three primary PDFs blocked at the proxy. |
| 6 | Incident inquiries | **Blocked.** Manchester Arena Inquiry, Casey Review and all gov.uk/inquiry hosts refused. Characterised from professional knowledge and marked [VERIFY]. |
| 7 | What they ask vendors | **Derived** from hops 2–6 rather than retrieved. Tender hop 3 gave the strongest direct evidence (demos and user testing as formal stages). |
| 8 | Simulator demands | **Derived.** The strongest chain is hop 4 → hop 8: if siting/staffing/process dominate outcomes and cannot be varied in a live pilot, simulation is the only instrument that can. |

### A.2 Chains for groups (b)–(g)

- **(b) CNI:** hops 1–2 satisfied largely by carrying forward R05 §1.2's retrieved
  NPSA/CAPSS/CSE wording. Hop 3 (CNI tenders) **not attempted — budget exhausted**;
  these are often not publicly advertised in useful detail anyway, which is itself
  a finding. Hop 4 (PIRs) is essentially unavailable publicly for CNI. Hop 6
  (incidents) characterised only: Moore County, Nord Stream, North Hyde/Heathrow
  — **and the brief's "UK substation arson 2025 Heathrow fire" framing is
  challenged in §3.3 as probably incorrect.**
- **(c) Border:** carried forward R05 §1.3–1.4's retrieved GAO/EFF/EUROSUR
  material; the GAO effectiveness-metrics critique, which is the commercially
  important part, is **[VERIFY]** because `gao.gov` is blocked. Tekever, CIBMS,
  Saudi northern border and Israel's barrier are all **[VERIFY]** with named
  places to check.
- **(d) Police:** doctrine hop satisfied from R03 §4.2 (Servator, hostile
  reconnaissance, NPSA) and §4.3 (GAO SPOT). Inquiry hop blocked. LFR/*Bridges*
  hop blocked. Tender hop succeeded via §2.3.
- **(e) Defence:** satisfied by carrying forward R06 §3's institutional map.
  Project Maven analyst-burden quotations **not retrieved** — marked.
- **(f) Events:** Green Guide, UEFA and Martyn's Law all **[VERIFY]**; the
  analytic argument (capacity and flow, not threat) is derived from the crowd-
  disaster pattern and is robust independent of the citations.
- **(g) Retail/corporate:** deliberately shallow per scope.

### A.3 The most valuable single hop, and why

**Hop 5 for group (a): Keval & Sasse.** A single retrieved sentence listing five
failure modes — *"poor configuration of technology, poor quality video recordings,
and a lack of system integration, as well as poor stakeholder communication and
too many cameras with too few operators"* — from interviews with 13 managers and
38 operators across 13 control rooms. **Not one of the five is detection
accuracy.** That sentence reorganises the entire product roadmap, and it took one
search. The general lesson for future research in this directory: **the
human-factors and criminology literature contains the requirements; the CV
literature contains only the metrics.**

### A.4 What to do next, in priority order

1. Open the three blocked PDFs (Keval & Sasse; Gill & Spriggs HORS 292; Norris &
   Armstrong chapter) from an unrestricted network and extract verbatim quotes and
   page numbers. This alone would upgrade a dozen claims from [VERIFY] to [Q].
2. Read Manchester Arena Inquiry Volume 1's CCTV chapter and extract the actual
   findings and recommendation numbers.
3. Confirm the Martyn's Law capacity thresholds, tiers and commencement dates —
   this determines the size of the Persona 8 market.
4. Get the current i-LIDS scheme document from NPSA, including the pass thresholds
   R03 §2.3 could not obtain.
5. Retrieve the GAO reports on CBP surveillance-technology effectiveness metrics
   and quote the metrics critique precisely.
6. Establish whether CCTV operator turnover has ever been publicly quantified
   (SIA statistics, BSIA / Skills for Security).
7. Verify the Heathrow / North Hyde cause and the review findings; correct §3.3.

---

## 17. Implications for this repository, stated as commitments

Seven concrete things this document argues the simulator should do, each traceable
to a user finding above. These are the actionable output.

1. **Emit i-LIDS-shaped corpora as a first-class output**: per scenario, ~24 h,
   all weather, all times of day, 2–3 views, with deliberate non-alarm content and
   event-level ground truth scored on a 10-second tolerance. (§13.1, R03 §2.)
2. **Report `Pmiss @ nuisance-alarms-per-camera-hour`, and additionally translate
   it into alarms-per-operator-shift at a stated camera:operator ratio.** The
   second number is the one the customer lives in. (NF1, §2.1.)
3. **Make camera health and integrity a simulated failure class**: dirt, defocus,
   occlusion, PTZ drift, freeze, signal loss, scene change — so that health
   analytics can be developed and benchmarked, since that is the shortest path
   into a CNI account. (F4, §3.4.)
4. **Support coverage and blind-spot analysis** over site geometry, producing a
   signed residual-blind-spot map as an artefact. (§13.2, Manchester Arena.)
5. **Generate demographically and physically stratified populations** — skin tone,
   body shape, gait, mobility aids, clothing — and report per-stratum performance
   as a required, not optional, output. (F15, §5.3, R03 §9.3.)
6. **Model density and flow with ground truth at 4+ persons/m²**, including
   arrival-rate versus processing-rate at ingress chokepoints, because that is the
   defensible crowd product. (F5, §5.5, §7.1.)
7. **Version and re-run an adversary-behaviour library** (`hard_negative_for` as a
   red-team artefact) against every model release. (§13.4, R03 §7.1.)

And one negative commitment, which is equally important: **the simulator should
not generate, and the product should not claim, emotion, deception or intent
inference from appearance.** The scientific basis is absent (GAO: 54%, chance),
the EU legal position is hostile, and the customers who matter know both. (§5.2,
R03 §4.3, §9.3.)

---

## Sources

### Retrieved this session (nine searches before budget exhaustion)

**Public-space CCTV operators and ethnography**
- Clive Norris & Gary Armstrong, *The Maximum Surveillance Society: The Rise of CCTV* (Berg, 1999) — [Internet Archive](https://archive.org/details/maximumsurveilla0000norr), [Taylor & Francis](https://www.taylorfrancis.com/books/mono/10.4324/9781003136439/maximum-surveillance-society-gary-armstrong-clive-norris)
- Norris & Armstrong, *CCTV and the Social Structuring of Surveillance* — [PDF (blocked at proxy)](https://popcenter.asu.edu/sites/g/files/litvpz3631/files/library/CrimePrevention/Volume_10/06-NorrisArmstrong.pdf)
- Gavin J. D. Smith, *Opening the Black Box: The Work of Watching* — [Routledge](https://www.routledge.com/Opening-the-Black-Box-The-Work-of-Watching/Smith/p/book/9781138200043), [Taylor & Francis](https://www.taylorfrancis.com/books/mono/10.4324/9780203519387/opening-black-box-gavin-smith), [Oxford Centre for Criminology review](https://blogs.law.ox.ac.uk/centres-institutes/centre-criminology/blog/2014/11/opening-black-box-work-watching), [review in *Journal of Sociology*](https://journals.sagepub.com/doi/10.1177/1440783315595327)
- Ahmed Keval & M. Angela Sasse, *"Not the Usual Suspects": A Study of Factors Reducing the Effectiveness of CCTV*, Security Journal 23(2):134–154 (2010) — [UCL Discovery](https://discovery.ucl.ac.uk/id/eprint/19823/), [PDF](https://discovery.ucl.ac.uk/19823/1/Keval_Sasse_Not_the_Usual_Suspects_Security_Journal_2010.pdf), [Springer](https://link.springer.com/article/10.1057/palgrave.sj.8350092), [OJP](https://www.ojp.gov/ncjrs/virtual-library/abstracts/not-usual-suspects-study-factors-reducing-effectiveness-cctv)
- Martin Gill & Angela Spriggs, *Assessing the Impact of CCTV*, Home Office Research Study 292 (2005) — [PDF](https://popcenter.asu.edu/sites/g/files/litvpz3631/files/Responses/video_surveillance/PDFs/Gill&Spriggs_2005.pdf), [OJP abstract](https://www.ojp.gov/ncjrs/virtual-library/abstracts/assessing-impact-cctv), [Semantic Scholar](https://www.semanticscholar.org/paper/Assessing-the-impact-of-CCTV-Gill-Spriggs/39d5c2c01ec6ae86ebbb4deed7822bf31af0c317)
- *Surveillance in Practice: Operators' Collective Interpretation of CCTV Images* — [Academia.edu](https://www.academia.edu/52644357/Surveillance_in_Practice_Operators_Collective_Interpretation_of_CCTV_Images)
- *CCTV as a tool for early police intervention: preliminary lessons from nine case studies*, Security Journal — [Springer](https://link.springer.com/article/10.1057/sj.2014.17)
- *How do police use CCTV footage in criminal investigations?* — [AIC tandi 575](https://www.aic.gov.au/publications/tandi/tandi575)

**Scale, staffing, licensing**
- [Westminster Labour: 100 more CCTV cameras (Feb 2025)](https://www.westminsterlabour.org.uk/issues/crime-and-public-protection/2025/02/07/100-more-cctv-cameras-in-westminster-labours-crackdown-on-crime-and-asb/)
- [Westminster City Council CCTV service](https://www.westminster.gov.uk/leisure-libraries-and-community/crime-and-community-safety/cctv-service) · [camera locations](https://www.westminster.gov.uk/leisure-libraries-and-community/crime-and-community-safety/cctv-service/camera-locations)
- [Comms Business: North awarded £1.2m Westminster CCTV contract](https://www.commsbusiness.co.uk/content/news/north-awarded-12-million-cctv-contract-by-westminster-city-council/) · [Networking+](https://networkingplus.co.uk/news-details?itemid=6273&post=westminster-to-become-safer-city-with-new-cctv-815121) · [GLA question: Westminster Council CCTV](https://www.london.gov.uk/who-we-are/what-london-assembly-does/questions-mayor/find-an-answer/westminster-council-cctv)
- Local-authority CCTV annual reports as a genre: [South Kesteven 2024-25](https://www.southkesteven.gov.uk/sites/default/files/2025-04/CCTV%20Annual%20Report%202024-2025%20%20New.pdf), [King's Lynn & West Norfolk 2022-23](https://www.west-norfolk.gov.uk/download/downloads/id/7975/cctv_annual_report_2022-2023.pdf), [St Albans 2019-20](https://www.stalbans.gov.uk/sites/default/files/attachments/CCTV%20Annual%20Report%202019-20.pdf)
- [Manchester City Council CCTV Code of Practice](https://www.manchester.gov.uk/downloads/download/7424/cctv_code_of_practice) · [update report](https://democracy.manchester.gov.uk/documents/s30147/Update%20of%20CCTV%20Code%20of%20Practice.pdf)
- SIA licensing and training: [SIA Training Hub, CCTV operator training 2026](https://siatraininghub.uk/cctv-operator-training-2026/), [licence requirements](https://siatraininghub.uk/cctv-licence-requirements-2026/), [Get Licensed](https://www.get-licensed.co.uk/licence/cctv-licence), [Tavcom](https://www.tavcom.com/courses/cctv-operator-training-course-public-space-surveillance-for-sia-licence/)

**Doctrine and regulation**
- [Amended Surveillance Camera Code of Practice (GOV.UK)](https://www.gov.uk/government/publications/update-to-surveillance-camera-code/amended-surveillance-camera-code-of-practice-accessible-version) · [guide to the 12 principles (PDF)](https://assets.publishing.service.gov.uk/government/uploads/system/uploads/attachment_data/file/1054263/Code_of_Practice-guide_to_the_12_principles.pdf) · [2013 code (PDF)](https://assets.publishing.service.gov.uk/media/619b7b50e90e07044a559c9b/Surveillance_Camera_CoP_Accessible_PDF.pdf) · [guide for local authorities](https://www.gov.uk/government/publications/surveillance-camera-code-of-practice-guidance-for-local-authorities/surveillance-camera-code-of-practice-a-guide-for-local-authorities-accessible) · [House of Lords Library: regret motion](https://lordslibrary.parliament.uk/surveillance-camera-code-of-practice-regret-motion/) · [CCTV Logbook summary of the 12 principles](https://www.cctvlogbook.com/2021/06/12-guiding-principles-a-framework-for-cctv-compliance/)

**Procurement**
- [Find a Tender](https://www.find-tender.service.gov.uk/) — [Kent CC, CCTV/Security/Access (005344-2025)](https://www.find-tender.service.gov.uk/Notice/005344-2025); [Sussex PCC, Automated Video Redaction (029956-2025)](https://www.find-tender.service.gov.uk/Notice/029956-2025?origin=SearchResults&p=1); [notice 062577-2025](https://www.find-tender.service.gov.uk/Notice/062577-2025); [notice 079605-2025](https://www.find-tender.service.gov.uk/Notice/079605-2025)
- [FVS: supporting local authorities with high street surveillance upgrades](https://www.fvs-cctv.com/blog/supporting-local-authorities-with-high-street-surveillance)

### Carried forward from sibling dossiers (re-verify before external use)

- NPSA: [PIDS](https://www.npsa.gov.uk/building-protection/video-surveillance-access-control-detection-control-rooms/perimeter-intrusion-detection-pids) · [Guide to PIDS (PDF)](https://www.npsa.gov.uk/system/files/documents/2c/80/Guide-to-PIDS.pdf) · [CAPSS](https://www.npsa.gov.uk/cyber-assurance-physical-security-systems-capss-evaluations) · [PIDS evaluation schemes](https://npsa.gov.uk/perimeter-intrusion-detection-systems-pids-evaluation-schemes) · [hostile reconnaissance](https://www.npsa.gov.uk/security-guidance/risks/hostile-reconnaissance) · [disrupting hostile reconnaissance](https://www.npsa.gov.uk/specialised-guidance/hostile-reconnaissance/disrupting-hostile-reconnaissance) · [Project Servator](https://www.npsa.gov.uk/national-security-act/countering-threat-sabotage-operations-uk-interests-national-security/project-servator) · [ProtectUK](https://www.protectuk.police.uk/hostile-reconnaissance)
- Servator evaluation: [comparison with routine stop and search, City of London](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11755829/)
- GAO on behaviour detection: [GAO-14-159](https://www.gao.gov/products/gao-14-159) · [GAO-14-158T](https://gao.gov/products/GAO-14-158T) · [GAO-17-608R](https://www.gao.gov/products/gao-17-608r) · [The Intercept on the SPOT checklist](https://theintercept.com/2015/03/27/revealed-tsas-closely-held-behavior-checklist-spot-terrorists/) · [House Homeland Security Democrats report](https://democrats-homeland.house.gov/news/reports/report-tsa-unable-scientifically-validate-behavior-detection-program)
- Border towers: [FedScoop on Anduril/CBP](https://fedscoop.com/anduril-sentry-towers-cbp/) · [EFF 2024](https://www.eff.org/deeplinks/2024/10/us-border-surveillance-towers-have-always-been-broken) · [EFF 2026](https://www.eff.org/deeplinks/2026/07/explosion-surveillance-towers-coming-us-borders-costing-over-1-billion) · [Reason 2026](https://reason.com/2026/07/30/homeland-security-is-spending-1-billion-on-autonomous-border-surveillance-towers/)
- EUROSUR: [European Commission](https://home-affairs.ec.europa.eu/policies/schengen/eurosur_en) · [Statewatch analysis](https://www.statewatch.org/analyses/2019/monitoring-secondary-movements-and-hotspots-frontex-is-now-an-internal-surveillance-agency/) · [Frontex Information Fusion Centre briefing](https://media.frag-den-staat.de/files/foi/821089/8-fx-eurosur-situational-awareness-at-external-borders-red.pdf) · [ITSS Verona critique](https://www.itssverona.it/european-border-surveillance-system-eurosur-and-its-problematic-impact-on-the-rights-of-the-people-on-the-move) · [Völkerrechtsblog](https://voelkerrechtsblog.org/under-eurosurs-watchful-eye/)
- i-LIDS: [i-LIDS standard paper](https://www.researchgate.net/publication/284353547_Imagery_Library_for_Intelligent_Detection_Systems_i-LIDS_A_Standard_for_Testing_Video_Based_Detection_Systems) · [Perimeter Intrusion Detection by Video Surveillance: A Survey (Sensors 2022)](https://www.mdpi.com/1424-8220/22/9/3601) · [PubMed record](https://pubmed.ncbi.nlm.nih.gov/35591289/)
- Human factors and alarm fatigue: [Applied Ergonomics 2012 (semi-automated CCTV, system confidence)](https://www.sciencedirect.com/science/article/abs/pii/S0003687012000695) · [Applied Ergonomics 2014 (work exposure and vigilance decrements)](https://www.sciencedirect.com/science/article/abs/pii/S0003687014001847) · [PLOS ONE 2014 (inattentional blindness in security monitoring)](https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0086157) · [Actuate on alarm fatigue](https://actuate.ai/alarm-fatigue/) · [Sandia/DOE on false and nuisance alarms](https://www.osti.gov/servlets/purl/1347158)
- Regulation: [ICO CCTV and video surveillance](https://ico.org.uk/for-organisations/uk-gdpr-guidance-and-resources/cctv-and-video-surveillance/) · [SCC/ICO DPIA guidance (PDF)](https://assets.publishing.service.gov.uk/media/5ea6f1fc86650c031af37947/SCC___ICO_DPIA_guidance_V3_FINAL_PDF.pdf) · [EU AI Act Article 5 FAQ](https://ai-act-service-desk.ec.europa.eu/en/ai-act/faq/what-systems-are-prohibited-under-article-5-ai-act-eg-social-scoring-emotion-recognition) · [FPF on the emotion-recognition prohibition](https://fpf.org/blog/red-lines-under-eu-ai-act-unpacking-the-prohibition-of-emotion-recognition-in-the-workplace-and-education-institutions/)
- Defence institutions: [Dstl](https://www.gov.uk/government/organisations/defence-science-and-technology-laboratory) · [DASA](https://www.gov.uk/government/organisations/defence-and-security-accelerator) · [Defence AI Centre](https://www.gov.uk/government/groups/defence-artificial-intelligence-centre) · [Home Office ACE](https://www.gov.uk/government/groups/accelerated-capability-environment-ace) · [Turing DARe](https://www.turing.ac.uk/science-innovation/defence-and-national-security/defence-artificial-intelligence-research-dare) · [Security & Policing](https://www.securityandpolicing.co.uk/) · [Halldale DSEI 2025 report](https://www.halldale.com/defence/dsei-2025-prepared-for-20-40-40)

### Named but unretrieved — the verification queue

Places to check, listed so the next person does not have to rediscover them:
[Manchester Arena Inquiry](https://www.manchesterarenainquiry.org.uk/) ·
[SGSA (Green Guide)](https://sgsa.org.uk/) ·
[ONR](https://www.onr.org.uk/) ·
[Ofgem](https://www.ofgem.gov.uk/) ·
[NESO](https://www.neso.energy/) ·
[The FA (Casey Review)](https://www.thefa.com/) ·
[Tekever](https://www.tekever.com/) ·
[BSF](https://www.bsf.gov.in/) ·
[Contracts Finder](https://www.contractsfinder.service.gov.uk/) ·
[NPSA](https://www.npsa.gov.uk/) ·
[ICO](https://ico.org.uk/) ·
[Bohemia Interactive Simulations](https://bisimulations.com/)

### Sibling dossiers in this directory

[R01 detection and single-camera tracking](./R01_detection_and_single_camera_tracking.md) ·
[R02 multi-camera tracking and re-ID](./R02_multicamera_tracking_and_reid.md) ·
[R03 behaviour, intent and anomaly detection](./R03_behaviour_intent_anomaly_detection.md) ·
[R04 degraded imaging and sim2real](./R04_degraded_imaging_and_sim2real.md) ·
[R05 multi-sensor fusion and NL retrieval](./R05_multisensor_fusion_and_nl_retrieval.md) ·
[R06 company, people and ecosystem](removed-vendor-doc.md) ·
[H01 veteran questions](./H01_veteran_questions_perception.md)

---

## Verification backlog (do these before any external use)

1. **Three blocked PDFs** — Keval & Sasse, Gill & Spriggs HORS 292, Norris &
   Armstrong. Extract verbatim text and page numbers. Highest value per minute of
   anything in this list.
2. **The HORS 292 "one of thirteen" claim** — currently **[VERIFY]** and
   deliberately not asserted.
3. **Manchester Arena Inquiry Volume 1** — CCTV findings and recommendation
   numbers; the blind-spot finding; the hostile-reconnaissance chronology.
4. **Martyn's Law** — capacity thresholds, tier definitions, regulator,
   commencement. Determines the Persona 8 market size.
5. **Casey Review (Euro 2020 final)** — actual findings and wording.
6. **Heathrow / North Hyde March 2025** — cause and review findings. **§3.3
   currently challenges the brief's "arson" framing; confirm.**
7. **GAO on CBP surveillance-technology effectiveness metrics** — report numbers
   and the metrics critique verbatim; also the "failed all six privacy
   protections" claim.
8. **Project Maven** — the analyst-burden quotations, from the DoD establishment
   memo.
9. **Dstl's published language** on human-machine teaming and cognitive burden —
   one primary-source quotation would strengthen §6.2 considerably.
10. **SGSA Green Guide** — current edition, capacity methodology terminology, CCTV
    and counting requirements.
11. **ONR SyAPs** — the security-assessment principle and TAG that a nuclear
    customer would cite for detection and assessment.
12. **CCTV operator turnover** — establish whether it has ever been publicly
    quantified.
13. **NERC CIP-014** — confirm scope and what it requires of physical security
    plans.
14. ***Bridges* v South Wales Police** and the **NPL evaluation of Met LFR** —
    the two documents behind every demographic-performance question.
15. **NDAA §889** — confirm which provision UK notices are actually invoking.

**Word count target met; epistemic status of every section marked. The most
important corrections this document makes to its own brief are: Westminster's
public-realm estate is ~200 cameras and six staff, not ~5,000 cameras (§2.1); the
2025 Heathrow-area substation fire was very probably not arson (§3.3); and the
governing user requirement in this market is a five-item list in which detection
accuracy does not appear (§2.5).**
