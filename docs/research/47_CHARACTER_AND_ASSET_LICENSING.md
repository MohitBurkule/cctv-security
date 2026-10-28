# 47 — Character and asset licensing for ML training/evaluation

*Written 2026-09-26. Not legal advice; it is the engineering reading of
published terms, meant to decide what the pipeline defaults to. Get counsel
before a sale. Tags: **[Q]** quoted verbatim from the source, **[S]**
summarised from a search-result snippet/secondary source (the primary page
refused automated fetch), **[INF]** our inference.*

## 0. Verdict first

**The MetaHuman clause [Q — re-fetched 2026-09-26 by plain `curl` from
https://www.metahuman.com/license (HTTP 200; the text sits in the page's FAQ
JSON-LD, so it is *not* login-walled — only tools that follow the optional SSO
redirect see a login page); matches doc 44 §8.1 and CG Channel, 4 June 2025]:**

> "You can use MetaHuman characters and animation in workflows that incorporate
> artificial intelligence technology. However, you may not use MetaHuman
> characters or animation curves to build or enhance any database or train or
> test artificial intelligence, machine learning, deep learning, neural
> networks, or similar technologies (as further detailed in the Unreal Engine
> EULA). This includes the use of rendered output from MetaHuman digital
> characters and animation curves, if created to replicate the functionality of
> MetaHuman."

The Unreal Engine EULA (unrealengine.com/eula/unreal; 403 to our fetcher,
text via search snippet [S]) carries the same wording: MetaHuman characters and
animation curves may not be used for "build or enhance any database or training
or testing any artificial intelligence, machine learning, deep learning, neural
networks, or similar technologies", and separately bars using Licensed
Technology as training input to a Generative AI Program.

**Verdict: the finding is true.** Rendering MetaHumans (bodies *or* the
`AS_MH_*` animation curves) into a detection/tracking/ReID dataset is "build a
database", and training *or evaluating* a model on it is "train or test".
The June 2025 change ("MetaHuman for UE" terms: free under US$1M revenue, usable
in any engine, sellable on marketplaces) widened *where* MetaHumans can be used;
it did **not** relax the AI clause.
The trailing "if created to replicate the
functionality of MetaHuman" sentence is ambiguous, but the operative first
sentence does not depend on it [INF].

*Audit note (2026-09-26).* A community post on the Epic forums
(https://forums.unrealengine.com/t/can-metahuman-be-used-for-ai-training-in-academic-purposes/2037347)
says the AI restriction in the UE Content EULA "MetaHuman Content Addendum" was
deleted when the NoAI tag was introduced, and quotes the separate MetaHuman
Creator EULA (unrealengine.com/eula/mhc) restriction (j): no use of "the
MetaHuman Technology for the purpose of building or enhancing any database or
training or testing any artificial intelligence, machine learning, deep
learning, neural network or similar technology". Whatever happened to that
addendum, the *current* metahuman.com licence page (fetched above) still
carries the prohibition, so the verdict stands; it is the page to cite.

**Consequence:** every frame in `out/batch_v4`, `batch_v5`, `batch_v6` (all
MetaHuman, driven by `AS_MH_Neutral_Walk_Loop_F`) and the docs/13 baseline
numbers computed on them are **internal engineering evidence only**. They must
not be used to train, fine-tune, validate or benchmark any model that is
shipped, sold, or quoted to a customer, unless Epic grants custom terms
("If you require custom legal terms ... Contact us").

## 1. Source texts

| Source | Operative text | URL / date |
|---|---|---|
| MetaHuman licence FAQ | clause above [Q] | https://www.metahuman.com/license (HTTP 200 via curl 2026-09-26; clause in FAQ JSON-LD) |
| Unreal Engine EULA | same MetaHuman AI/ML restriction + no use as Generative-AI training input [S] | https://www.unrealengine.com/eula/unreal (403, 2026-09-26) |
| MetaHuman licence change | "workflows that incorporate artificial intelligence technology" allowed; may not "train or enhance the AI models themselves" [Q of the article, not of Epic]; free under US$1M annual revenue, above it UE seats at US$1,850/yr; article dated 4 Jun 2025 | https://www.cgchannel.com/2025/06/you-can-now-sell-metahumans-or-use-them-in-unity-or-godot/ |
| Fab marketplace EULA | Standard/Personal/Professional tiers; per-listing "NoAI" flag — **not fetched** (403). Treat every Fab asset as ML-prohibited until its listing and the Fab EULA are read by hand. | https://www.fab.com/eula |
| SMPL-X model licence | "for the sole purpose of performing non-commercial scientific research, non-commercial education, or non-commercial artistic projects"; "Any other use, in particular any use for commercial, pornographic, military, or surveillance, purposes is prohibited"; and "This license also prohibits the use of the Software to train methods/algorithms/neural networks/etc. for commercial, pornographic, military, surveillance, or defamatory use of any kind." [Q, re-fetched 2026-09-26] | https://smpl-x.is.tue.mpg.de/modellicense.html, 2026-09-26 |
| BEDLAM licence | same wording, with "Data & Software" in place of "Model & Software", incl. **surveillance** ban [Q, re-fetched 2026-09-26] | https://bedlam.is.tue.mpg.de/license.html, 2026-09-26 |
| SMPL commercial | via Meshcapade / smpl@max-planck-innovation.de — negotiated, price not public | same pages |
| Reallusion Content EULA (updated 1 Aug 2025) | Standard licence prohibits use "For machine learning, AI training, or AI-generated output." (§2.1.2.C.5 — list item 5 under "You may NOT use the Content or any Derivative Content in the following scenarios or applications:") [Q, re-fetched 2026-09-26, page dated August 1st, 2025]; Enterprise licence negotiable for ML | https://www.reallusion.com/Content/EULA/EULA.htm ; https://www.reallusion.com/license/enterprise.html |
| Mixamo (Adobe) | royalty-free for commercial projects, but Adobe staff state bulk download / ML-training use is not allowed [S, community + FAQ 403] | https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html |
| CesiumMan (glTF sample) | "© 2017, Cesium. Creative Commons Attribution 4.0 International" [Q] — **CC-BY, not CC0**: commercial + ML fine, attribution required | https://github.com/KhronosGroup/glTF-Sample-Assets/blob/main/Models/CesiumMan/README.md |
| Quaternius (poly.pizza) | CC0 per model page; quaternius.com meta: "hundreds of free Low Poly 3D Models, using the CC0 License." [Q]; `~/data/assets/index.json` records all 57 downloaded assets as `CC0-1.0` [V] | poly.pizza/m/<id>; https://quaternius.com |
| Kenney | `License.txt`: "Creative Commons Zero, CC0"; support page: "all game assets on the asset pages are public domain licensed (CC0)" [Q] | https://kenney.nl/support |
| ambientCG | "provided under the Creative Commons CC0 1.0 Universal License" [Q] | https://docs.ambientcg.com/license/ |
| Poly Haven | "Our assets are all licensed as CC0" [Q] | https://polyhaven.com/license |
| RenderPeople / Daz3D | not fetched this pass. RenderPeople sells scans of real people (likeness + ML terms per product); Daz standard EULA historically excludes ML without an "Interactive/ML" licence. **Assume prohibited until read.** [INF] | renderpeople.com, daz3d.com |
| Synthesis AI / Datagen-style vendors | commercial synthetic-human datasets/APIs sold *for* ML training under negotiated contract; Datagen ceased operations 2024 [INF, not re-verified] | — |

CC0 is a public-domain dedication with no field-of-use restriction, so ML
training, surveillance use and sale of derived models are all permitted; CC0
does not grant trademark, patent or likeness rights (CC0 §4a: "No trademark or
patent rights held by Affirmer are waived"; irrelevant for stylised rigs).

## 2. Risk table (assets SurvSim actually uses)

| Asset class | Licence | Commercial ML use | Affected data |
|---|---|---|---|
| MetaHuman bodies (editor route, `mh_*.py`, `rig_from_dna.py`) | UE EULA + MetaHuman terms | **Prohibited** (train *and* test) | batch_v4, v5, v6; docs/13 baselines on them; any `mh_lineup`/`mh_prod_render` output |
| `AS_MH_*` walk loops (MetaHumanCharacter plugin) | same — "animation curves" | **Prohibited**, even on non-MetaHuman bodies | any render animated by them; `walk_foot_curves.py` outputs |
| Other Epic engine content (Manny/Quinn, starter content, UnrealZoo cooked maps) | UE EULA / Epic Content Licence; UnrealZoo map provenance mixed | **Unclear** — read UE EULA AI section by hand; UnrealZoo scenes come from Fab/Marketplace packs with per-pack terms | all UnrealZoo/unreal-backend renders (batch_v1–v3 backgrounds) |
| Quaternius rigs (raw + `characters_rebake/`) | CC0 | **Permitted** | none |
| CesiumMan | CC-BY 4.0 | **Permitted with attribution** in dataset/model docs | batch_v3 |
| Kenney props/vehicles | CC0 | Permitted | none |
| ambientCG textures | CC0 | Permitted | none |
| Poly Haven HDRIs | CC0 | Permitted | none |
| Mock backend (pure Python) | ours | Permitted | none |
| MOT20 (real footage, for validation) | CC BY-NC-SA 3.0 | **Non-commercial only** — fine for internal metric validation, not for training a sold model [INF; the MOT20 data page did not state the licence when fetched 2026-09-26 — unverified here] | tracking-metric validation only |
| LLVIP (real night visible + thermal pairs; 50 sample frames in `~/data/real_cctv_night`) | Non-commercial research ("freely available … for non-commercial purposes such as academic research", homepage, [V] 2026-09-27) | **Non-commercial only** — realism measurement (H32), never training | docs/15 night band, 69 §7 |
| KAIST multispectral | CC BY-NC-SA 4.0 ([V] repo) | **Non-commercial only**; not downloaded (1.44 GB preview > budget) | none |
| FLIR ADAS v2 | form-gated; terms page 404 on 2026-09-27 — **unverified** | **Treat as blocked** | none |
| M3FD (TarDAL) | repo code GPL-3.0; **no dataset licence stated** | **Unclear → blocked** | none |

## 3. Recommended licence-compliant character stack

| Option | Licence cost | Realism at CCTV standoff | Notes |
|---|---|---|---|
| **A. Rebaked Quaternius CC0 + procedural/painted clothing (default)** | £0 | Low-poly, stylised; adequate at 720p/≥10 m once textured and degraded, poor close-up | Already [V] rebaked to 175 cm; zero licence risk; limited body diversity (22 rebaked, **16 verified** usable on their own clips per commit 9c87424; some chibi) |
| B. Own-built / commissioned bodies (Blender, MakeHuman CC0 export) | artist time | Medium–high | MakeHuman exports are CC0 [INF — verify version terms]; full ownership |
| C. SMPL-X under Meshcapade commercial licence | negotiated (typically 5-figure/yr) [INF] | High body-shape diversity, no clothing | **Academic licence bans surveillance explicitly**; commercial licence must name surveillance use; BEDLAM assets not included |
| D. Reallusion CC characters under **Enterprise** licence | negotiated | High, clothed, rigged, exports to UE | Standard licence forbids ML; only Enterprise works |
| E. Licensed synthetic-human vendor data (Synthesis-AI-style) | contract | High | Buys data, not a simulator; loses our GT control |
| F. MetaHuman under custom Epic terms | negotiated | Highest | Only way to keep batch_v4–v6 usable |

**Recommendation:** A as the default now; pursue F (one email to Epic) and B
in parallel; C/D only if a customer funds it.

Changes needed in `scripts/ue` (status 2026-09-26 — **done**: CC0 default in
`tools/render_run.py`, own Quaternius clips, vertex-colour clothing,
`asset_licences` + `commercial_ml_ok`, CesiumMan attribution; **open**: the
`--licence-restricted` flag on the `mh_*` scripts and eval refusing product
numbers on a non-commercial set; see docs/12 "CC0 characters"):
- `mh_prod_render.py`, `mh_job_runner.py`, `mh_lineup.py`, `mh_bake.py`,
  `mh_postprocess.py`, `rig_from_dna.py`, `build_character.py`: gate behind an
  explicit `--licence-restricted` flag; refuse to write into a dataset tagged
  commercial.
- Replace `AS_MH_Neutral_Walk_Loop_F` (mh_prod_render.py:30,
  walk_foot_curves.py:6) with the Quaternius CC0 walk clips carried in the
  rebaked glTFs.
- `import_character.py` / `import_gltf.py`: default to `characters_rebake/*_r`
  and read `license` from `~/data/assets/index.json`.
- `survsim_clothing.py`, `survsim_materials.py`: clothing variation by
  procedural materials on CC0 meshes (ambientCG textures) instead of the
  MetaHuman wardrobe.
- `render_run.py` / `job_runner.py` / GT writers: emit a per-frame
  `asset_licences` field (set of SPDX-style ids) and a dataset-level
  `commercial_ml_ok` boolean; eval refuses to report "product" numbers on a
  set where it is false.
- Add CC-BY attribution output for CesiumMan when used.

## 4. If asked "can you sell models trained on this?"

> "Not on the MetaHuman renders. Epic's MetaHuman terms say MetaHuman
> characters and animation curves may not be used to build a database or to
> train or test AI, so the batches rendered with MetaHumans are internal
> engineering evidence only. The pipeline itself is ours, and it now defaults
> to characters, textures and HDRIs that are CC0 — public domain, with no
> field-of-use restriction — so data rendered with that stack, and models
> trained on it, can be sold. Every frame records which asset licences it
> depends on, so we can prove the provenance of any training set. If we need
> MetaHuman-level realism in a product we would negotiate custom terms with
> Epic or licence commercial human assets, and we'd check real-footage sets
> like MOT20, which are non-commercial, are only used for validation."

## 5. Open items
- Read by hand (browser, logged in): UE EULA AI section, Fab EULA + NoAI flag,
  RenderPeople, Daz, Mixamo terms — all refused automated fetch.
- Establish provenance/licence of UnrealZoo cooked maps before any product use.
- Verify MakeHuman export licence for option B.

## 6. Audit (2026-09-26)

| claim | § | source | verdict |
|---|---|---|---|
| MetaHuman AI clause wording | 0, 1 | metahuman.com/license (curl, 200) | confirmed verbatim |
| metahuman.com/license "login-walled" | 1 | same | corrected — publicly served |
| UE EULA carries same wording | 0, 1 | unrealengine.com/eula/unreal (403) | unverifiable [S] |
| CG Channel June 2025 change, AI quote | 0, 1 | cgchannel.com (fetched) | confirmed; date 4 Jun 2025, US$1M / US$1,850 added |
| Content-addendum AI clause removed (forum) | 0 | Epic forum 2037347 | added; does not change verdict |
| SMPL-X sole-purpose / surveillance / training clauses | 1 | smpl-x modellicense (curl) | confirmed verbatim |
| BEDLAM "identical" | 1 | bedlam license (curl) | corrected — "Data & Software" |
| Reallusion §2.1.2.C.5, 1 Aug 2025 | 1 | reallusion EULA (fetched) | confirmed verbatim |
| CesiumMan CC-BY 4.0 | 1 | Khronos README (raw) | confirmed |
| Quaternius / Kenney / ambientCG / Poly Haven CC0 | 1 | sites (curl) + index.json | confirmed |
| 22 Quaternius bodies | 3 | commit 9c87424 | corrected — 16 verified of 22 |
| CC0 no trademark rights | 1 | CC0 1.0 §4a | confirmed; patents added |
| MOT20 CC BY-NC-SA 3.0 | 2 | motchallenge.net/data/MOT20 | unverifiable (not on page) |
| Mixamo, Fab, RenderPeople, Daz, Datagen | 1 | 403 / not fetched | unverifiable (already tagged) |

Score: 9 confirmed of 14 rows (64 %); 3 corrected, 2 unverifiable-or-added.
No correction changes the verdict: MetaHuman renders remain ML-prohibited;
CC0 stack remains permitted.
