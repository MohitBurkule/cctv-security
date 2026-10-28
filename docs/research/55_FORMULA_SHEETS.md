
One block per topic: **formula → symbols/units → the sentence you say while
writing it → source**. Every formula is copied from the deep dive that cites
a fetched primary source (cited as `doc §`). Former **[VERIFY]** items were
checked symbol-by-symbol against a fetched primary source on 2026-09-26
(see `AUDIT_55-56.md`); the source is now given inline. Arithmetic in examples is
re-derived in the cited section.

---

## 1. Detection geometry and post-processing

**IoU.** `IoU(A,B) = |A∩B| / (|A| + |B| − |A∩B|)`. Unitless, [0,1].
Example: (0,0)–(10,10) vs (5,5)–(15,15): 25/175 = **0.143** (`40` §A1, `42` #1).
*Say:* "Overlap over union — and on a 10-px-wide person a 2-px shift costs a third of it." (`25` §2.3: 160/240 = 0.667.)

**DIoU / CIoU loss** (`25` §2.3, Zheng et al.):
`L_DIoU = 1 − IoU + ρ²(b,b_gt)/c²`; `L_CIoU = L_DIoU + αv`,
`v = (4/π²)(arctan(w_gt/h_gt) − arctan(w/h))²`, `α = v/((1−IoU)+v)`.
ρ = centre distance (px), c = diagonal of smallest enclosing box (px).
*Say:* "1 − IoU has no gradient when boxes don't touch; DIoU adds centre distance, CIoU adds aspect ratio."

**GIoU** (Rezatofighi et al. CVPR 2019, arXiv 1902.09630, Alg. 1 — fetched): `GIoU = IoU − |C \ (A∪B)|/|C|`, C = smallest enclosing box; GIoU ∈ (−1, 1] (→ −1 as boxes separate far apart), loss `1 − GIoU` ∈ [0,2).
*Say:* "Same idea as DIoU but penalises empty area of the enclosing box."

**Greedy NMS** (`25` §2.7; Ultralytics `iou`=0.7): sort by score; keep top box
b_m; delete every b_i with IoU(b_m,b_i) > N_t; repeat. O(n²).
*Say:* "It deletes the second person when two people overlap above N_t — the crowd failure."
**DIoU-NMS** (`25` §2.7): suppress only if `IoU − ρ²/c² ≥ ε`.
**Soft-NMS** (Bodla et al. ICCV 2017, arXiv 1704.04503 §3 — fetched):
linear `s_i ← s_i(1 − iou(M,b_i))` if iou ≥ N_t, else unchanged; Gaussian `s_i ← s_i·exp(−iou(M,b_i)²/σ)` for **every** remaining b_i ∉ D (no N_t threshold), re-applied each iteration; O(N²) overall.

## 2. AP / mAP (COCO 101-point) and operating points

`P = TP/(TP+FP)`, `R = TP/(TP+FN)`, `F1 = 2PR/(P+R)`.
TP = detection matched greedily in score order to an unmatched GT at IoU ≥ t (`25` §4.1).

**COCO AP** (`25` §4.1, pycocotools): make precision monotone by backward sweep
`p̃(r_k) = max_{j≥k} p(r_j)`; sample at 101 recall points r ∈ {0, 0.01, …, 1};
unreached recall contributes 0:
`AP_t = (1/101) Σ_{r∈{0,…,1}} p̃(r)`; `AP50:95 = mean over t ∈ {0.50,0.55,…,0.95}` (and classes).
Area bins: small < 32², medium 32²–96², large > 96² px². maxDets 100 by default.
Worked (`25` §4.2): 5 GT, 8 dets → AP = (21 + 20 + 15 + 13.33)/101 = **0.686** (all-point: 0.683).
*Say:* "The missed person caps recall at 0.8 and costs ~0.2 AP; FPs after the last TP cost nothing — that's why AP flatters a system that drowns an operator."
*Also:* val runs conf 0.001 to trace the PR tail; a mAP at conf 0.25 is truncated (`25` §2.7).

**Operating point → alarms** (`42` #10, `28` §6.2): `FP/cam-h = FP_per_frame × fps × 3600`.
0.01 × 5 × 3600 = **180/cam-h**, 1,800× a 0.1/h budget. At 1 % FPR on a 24/7 camera: 0.01 × 1,440 = **14.4 alarmed min/day** (`42` #12).

## 3. Dense-detector losses

**Focal loss** (`25` §1.2, Lin et al.): `FL(p_t) = −α_t (1 − p_t)^γ log p_t`, γ = 2, α = 0.25.
p_t = model probability of the true class (Lin et al. arXiv 1708.02002: γ = 2, α = 0.25 best — fetched). p_t=0.9: CE 0.105 → (1−p_t)^γ·CE = 0.00105 (100× smaller); p_t=0.1: CE 2.303 → 1.87 (`40` §A5). **These omit α_t**; with α_t = 0.25 they are 0.00026 and 0.47 (α_t is 0.75 for a negative).
*Say:* "~10⁵ anchors, ~1:1000 fg:bg; γ removes the easy-negative mass, then α = 0.25 re-balances the other way."

**DFL** (`25` §2.2, GFL): predict softmax S over bins y_0…y_n; `ŷ = Σ_j S_j y_j`;
`DFL(S_i,S_{i+1}) = −((y_{i+1} − y) log S_i + (y − y_i) log S_{i+1})`.
Target 3.4 → S_3 = 0.6, S_4 = 0.4. reg_max = 16 ⇒ max distance 15 strides (120 px at P3).
*Say:* "An edge becomes a distribution, so an occluded edge can say 'I'm not sure'."

**Varifocal / QFL** (`25` §2.4): `VFL = −q(q log p + (1−q) log(1−p))` if q>0; `−α p^γ log(1−p)` if q=0; q = IoU target.
**TAL metric** (`25` §2.5; TOOD arXiv 2108.07755 — fetched): `t = s^α u^β` (Ultralytics α=0.5, β=6, topk=10; the TOOD paper itself uses α=1, β=6).
**YOLOv8 total** (`25` §2.6): `7.5·L_CIoU + 0.5·L_BCE + 1.5·L_DFL`.

**ECE** (`25` §5.1): `ECE = Σ_m (|B_m|/n)|acc(B_m) − conf(B_m)|`. Worked 0.105.
Temperature: `p = σ(z/T)` — ranking, hence AP, unchanged (`25` §5.2).

## 4. Kalman filter for a bbox tracker

State (`26` §2.3, DeepSORT/repo): `x = [u, v, a, h, u̇, v̇, ȧ, ḣ]ᵀ ∈ ℝ⁸`
(centre px, aspect ratio, height px, and their per-frame rates). BoT-SORT uses (x,y,w,h).
`F = [[I₄, I₄],[0, I₄]]` (Δt = 1 frame), `H = [I₄ 0₄]`.
Noise, height-scaled (BoT-SORT, `26` §2.3):
`Q = diag((σ_p w)²,(σ_p h)²,(σ_p w)²,(σ_p h)², (σ_v w)²,(σ_v h)²,(σ_v w)²,(σ_v h)²)`,
`R = diag((σ_m w)²,(σ_m h)²,(σ_m w)²,(σ_m h)²)`, σ_p = σ_m = 1/20, σ_v = 1/160.

Predict: `x⁻ = F x`, `P⁻ = F P Fᵀ + Q`.
Update: `y = z − H x⁻`, `S = H P⁻ Hᵀ + R`, `K = P⁻ Hᵀ S⁻¹`, `x = x⁻ + K y`, `P = (I − K H) P⁻`.
1-D drill (`42` #2): x=[10,1], P=diag(4,1), R=1, z=12 → x⁻=[11,1], P⁻=[[5,1],[1,1]], K=[5/6,1/6], **x=[11.833,1.167]**, P=[[0.833,0.167],[0.167,0.833]].
*Say:* "The KF isn't a smoother here — it produces the predicted box that IoU matching uses; a bad prediction is an ID switch."

## 5. Hungarian assignment with gating

`min Σ_ij C_ij X_ij` s.t. `Σ_j X_ij ≤ 1`, `Σ_i X_ij ≤ 1`, `X_ij ∈ {0,1}` (`26` §3.2).
Cost `C = 1 − IoU` (or `λ·d_Mahal + (1−λ)·d_cos` for appearance trackers).
**Gating:** set `C_ij = ∞` (repo evaluator: 1e6) where IoU < τ **before** solving, so the solver never spends a track on an invalid pair (`26` §3.4).
Complexity: Kuhn (1955) / Munkres (1957, J. SIAM 5(1):32–38) as originally stated is **O(n⁴)**; the **O(n³)** version is due to Edmonds & Karp (1972, J. ACM 19(2):248–264, doi:10.1145/321694.321699) and independently Tomizawa (1971, Networks 1(2):173–194). Say "O(n³) with the Edmonds–Karp/Tomizawa improvement". SciPy uses modified Jonker–Volgenant (`26` §3.2).
Drill (`42` #3): `[[4,1,3],[2,0,5],[3,2,2]]` greedy 6, optimal **5**. IoU example (`26` §3.3): greedy 0.6 + lost track vs optimal 1.05.
*Say:* "Greedy lets the first track steal a detection; that manufactures ID switches."

## 6. ByteTrack two-stage association (`26` §5.3)

1. KF-predict all tracks T. 2. Split detections: `D_high = {s > τ_high}` (τ = 0.6), `D_low = {τ_low < s ≤ τ_high}`.
3. Match T ↔ D_high (IoU/ReID, Hungarian; reject IoU < 0.2).
4. Match remaining T ↔ D_low by **IoU only**; unmatched D_low discarded.
5. Unmatched D_high → new tracks; unmatched tracks → lost, kept 30 frames.
*Say:* "Low-score boxes are often occluded people: they may rescue a track, never create one." MOT17 80.3 MOTA / 77.3 IDF1 / 63.1 HOTA.
OC-SORT cost: `C = C_IoU + λ C_v` with `Δθ = |θ_track − θ_intention|` (`26` §5.4).

## 7. MOTA / IDF1 / HOTA (`26` §6, Luiten et al.)

`MOTA = 1 − (FN + FP + IDSW)/GT` · `MOTP = mean S over TPs`.
`IDF1 = 2·IDTP/(|gtDet| + |prDet|)` (one-to-one trajectory bijection, global).
`DetA_α = TP/(TP+FN+FP)`; `A(c) = |TPA|/(|TPA|+|FNA|+|FPA|)`; `AssA_α = (1/|TP|) Σ_c A(c)`;
`HOTA_α = √(DetA_α·AssA_α)`; `HOTA = (1/19) Σ_{α=0.05..0.95} HOTA_α`.

**Tiny worked example** (`26` §6.4): GT A,B over 3 frames, pred IDs 1,2,3.
f1: A→1, B→2 · f2: A→2, B missed, FP id3 · f3: A→2, B→1. TP 5, FN 1, FP 1, IDSW 2.
MOTA = 1 − 4/6 = **0.333**; IDF1 best bijection {A↔2,B↔1} IDTP 3 → **0.500**;
DetA = 5/7 = 0.714; pair Jaccards (A,1).25 (A,2).50×2 (B,2).20 (B,1).25 → AssA = **0.340**; HOTA₀.₅ = **0.493** (over all α: 0.403).
Second drill (`42` #4): 1 GT × 4 frames, IDs a,a,b,b + 1 FP → HOTA 0.632, MOTA 0.5, IDF1 0.444.
*Say:* "DetA 0.71 ≫ AssA 0.34 — HOTA tells you it's the association half that's broken; MOTA can't."

## 8. ReID losses and metrics (`27` §2, §4)

**ID loss:** `L_ID = −Σ_j q_j log p_j`, label-smoothed `q_true = 1 − (N−1)ε/N`, else ε/N, ε = 0.1.
**Triplet (batch-hard):** `L = Σ_a [m + max_p D(a,p) − min_n D(a,n)]_+`; PK batch (P=18, K=4). Soft-margin: `ln(1+e^x)`.
On unit sphere `d² = 2 − 2cosθ ∈ [0,4]` (`42` #6). Drill: m=0.3, d_ap=0.8, d_an=1.0 → **0.1**.
**Circle:** `L = log[1 + Σ_j exp(γα_n(s_n − Δ_n)) · Σ_i exp(−γα_p(s_p − Δ_p))]`, `α_p=[1+m−s_p]_+`, `α_n=[s_n+m]_+`, `Δ_p=1−m`, `Δ_n=m`; γ≈128, m≈0.25.
*Say:* "Softmax cares the right class wins; metric losses care the cluster is tight."

**CMC:** `CMC(k) = (1/|Q|) Σ_q 1[r(q) ≤ k]`. **AP:** `AP(q) = (1/G_q) Σ_k P@k·hit(k)`; mAP = mean.
Worked: ✓✗✓✗✗✓ → 0.722; ✗✗✓✓✗✗ → 0.417; Rank-1 50 %, Rank-5 100 %, mAP **0.569**.
*Say:* "Rank-5 100 % and mAP 57 % means a third of sightings are buried — investigators need mAP."

## 9. Camera geometry (`29` §1–3)

`X_c = R X_w + t`, `t = −R C`; `x_n = X_c/Z_c`; `[u v 1]ᵀ = K[x_n y_n 1]ᵀ`;
`K = [[f_x, s, c_x],[0, f_y, c_y],[0,0,1]]` (f in **pixels**).
`P = K[R|t]`: 3×4, **11 DOF** (5 intrinsic + 3 R + 3 t).
`f_x = (W/2)/tan(HFOV/2)`: 1920 px, 70° → **1371 px**.
**Ground homography:** Z=0 ⇒ `H = K[r₁ r₂ t]`, **8 DOF**, ≥ 4 points (no 3 collinear); image→ground `[X Y 1]ᵀ ∝ H⁻¹[u v 1]ᵀ`.
*Say:* "Back-project the foot point, never the box centre; H dies when the PTZ moves."
**Brown–Conrady** (OpenCV order k1,k2,p1,p2,k3), r² = x'² + y'²:
`x'' = x'(1 + k₁r² + k₂r⁴ + k₃r⁶) + 2p₁x'y' + p₂(r² + 2x'²)`
`y'' = y'(1 + k₁r² + k₂r⁴ + k₃r⁶) + p₁(r² + 2y'²) + 2p₂x'y'`. k₁ < 0 barrel.
**Pixel height:** `px ≈ f_x H / R` (≈10 % error vs exact projection, `29` §7.2).

## 10. DORI and pixel density (`29` §6)

`px/m ≈ f_x / R` ⇒ `R_max = f_x / D`. DORI 2014: **25 / 62.5 / 125 / 250 px/m** (Detect/Observe/Recognise/Identify); ×0.16 m ⇒ px/face 4/10/20/40.
IEC 62676-4:2025: 20/40/80/125/250/500/1500 (Overview…Scrutinize).
cam_gate f=1371: Identify ≤ **5.5 m**, Detect ≤ 55 m.
*Say:* "DORI is a human-viewing standard; the detector's threshold is our own 20-px rule."

## 11. Exposure (`30` §6.3, `40` §A8)

`EV100 = log₂(N²/t) − log₂(S/100)` (N f-number, t seconds, S ISO).
f/1.6, 1/50 s, ISO 1600: log₂128 − log₂16 = **3** (dim street).
Blur = v·t·(px/m): 1.4 m/s × 0.02 s × 100 px/m ≈ **3 px**.
Probe correction ΔEV = log₂(measured/100): luma 43 → −1.22 EV → 2.3× brighter. UE: `auto_exposure_bias = −EV100`.
*Say:* "One stop is a factor of two; AE slows the shutter before it adds gain, so night means blur then noise."

## 12. H.264 GOP / bitrate arithmetic (`43` §3, §8; `53` §1.2; `40` §A9)

GOP period = GOP_frames / fps: 50 / 25 = **2 s** (noise frozen in skip blocks, refreshed at each I-frame ⇒ "pumping").
B-frame latency ≥ n_B / fps: 2 B at 25 fps ≥ **80 ms**.
Storage `bytes/day = Mbit/s × 10⁶ × 86 400 / 8`: 4 Mbit/s → **43.2 GB/day**, 1.30 TB/30 d; H.265 2.4 → 25.9 GB/day.
Network: 40 cams × 4 Mbit/s = **160 Mbit/s** main; 40 × 1 = 40 Mbit/s sub-streams.
*Say:* "Temporal statistics depend on GOP phase and bitrate; I-frame-only evaluation overstates field accuracy."

## 13. Statistics (`49`)

**Binomial SE:** `√(p(1−p)/n)`; n=10, p=0.8 → 0.126 (`49` §1.2).
**Wilson 95 %** (Wilson 1927, JASA 22:209–212, doi:10.1080/01621459.1927.10502953; form checked against NIST/SEMATECH e-Handbook §7.2.4.1 — fetched):
`(p̂ + z²/2n ± z√(p̂(1−p̂)/n + z²/4n²)) / (1 + z²/n)`, z = 1.96. 8/10 → **[0.49, 0.94]**; Clopper–Pearson [0.44, 0.97].
**Rule of three:** 0 events in T ⇒ 95 % upper `λ < −ln(0.05)/T ≈ 3/T` (`49` §5). 400 cam-h → < 0.0075/cam-h; 0.001 needs ~3,000 cam-h.
**Garwood exact Poisson:** upper `χ²₀.₉₇₅(2k+2)/2T`, lower `χ²₀.₀₂₅(2k)/2T`.
**Bootstrap:** resample the unit you generalise over (sequences/cameras/blocks, never frames); 2.5/97.5 percentiles (`49` §1.1).
**Power / seeds:** `n per arm ≈ 2(z₀.₉₇₅ + z₀.₈)² σ²/Δ² = 15.7 σ²/Δ²`; σ=0.025, Δ=0.02 → **25 seeds/arm** (`49` §2.2). Paired: Δ/s_d ≥ 2.8 (`49` §6).
**Permutation floor:** 3 vs 3, all ordered → p = 1/C(6,3) = 0.05 (`49` §2.3).
**McNemar:** `χ² = (b − c)²/(b + c)` on discordant pairs; exact binomial if b+c < 25 (`49` §7).
**Holm:** sort p; compare k-th smallest to `α/(m − k + 1)`; stop at first failure (`49` §4).
*Say:* "Zero false alarms in 30 hours only says the rate is under 0.1 an hour."

## 14. Multi-target tracking (`37` §3)

**PDA/JPDA likelihood** (Stone Soup `PDAHypothesiser`): `L_j = N(z_j; ẑ, S)·P_D/λ`, `S = HPHᵀ + R`; miss weight `1 − P_D P_G`.
JPDA: enumerate joint hypotheses (each z to ≤ 1 track), product of weights, normalise, marginalise to β_{t,j}; update with `x = x⁻ + K Σ_j β_j y_j` (β-mixture reduced to one Gaussian).
Worked: β_A = (0.001, **0.665**, 0.333) over (miss, z₁, z₂).
*Say:* "JPDA hedges instead of committing; the price is coalescence of two tracks walking together."
**GM-PHD one-liner** (Vo & Ma, IEEE TSP 54(11):4091–4104, 2006; author preprint fetched, eqs. 32–33): propagate the intensity `D(x) = Σ_i w_i N(x; m_i, P_i)`; expected target count `N̂ = ∫D = Σ_i w_i`; update: miss copy `(1−P_D)w_i`, plus per measurement z `w_i(z) = P_D w_i q_i(z) / (κ(z) + P_D Σ_l w_l q_l(z))`, `q_i(z) = N(z; H m_i, R + H P_i Hᵀ)`, κ = clutter intensity. *Say:* "Tracks the density of targets, not labelled tracks — count is the integral."

## 15. Edge / neuromorphic

**INT8 symmetric** (`25` §6.1, `38` §2.1, TensorRT): `s = max|x|/127`, `q = clip(round(x/s), −127, 127)`, `x̂ = s·q`.
Max 20 → s = 0.157, everything < 0.079 rounds to 0; clip at 6 → s = 0.047 (3.3× finer, saturates tail).
Affine adds zero-point z: `q = round(x/s) + z` (costly, `25` §6.1). Weights per-channel, activations per-tensor.
*Say:* "INT8 hurts small objects first — check per height band, calibrate on night and rain."

**LIF neuron.** Continuous form (Gerstner et al., *Neuronal Dynamics* §1.3, online — fetched): `τ_m du/dt = −(u − u_rest) + R I(t)`; fire when u = ϑ, then reset u → u_r (hard reset). The discrete form below is the SNN-training convention (`D05`; `36` §3; snnTorch-style), **not** Gerstner's text:
`V[t] = β V[t−1] + Σ_i w_i s_i[t]`, `β = exp(−Δt/τ_m)`; `s[t] = Θ(V[t] − V_th)`; soft reset `V ← V − V_th s[t]`.
Surrogate gradient: replace `∂Θ/∂V` by a smooth pseudo-derivative for BPTT (`36` §3).
*Say:* "Leak, integrate, fire, reset; timesteps are the SNN's bit-width — so compare against INT8, not FP32."

---

### Provenance summary
Fetched-source formulas: IoU, DIoU/CIoU, NMS, COCO AP, focal, DFL, VFL, TAL, ECE, KF, ByteTrack, MOTA/IDF1/HOTA, ID/triplet/circle, CMC/mAP, pinhole/K/H, Brown, DORI, EV100, JPDA, INT8, rule of three, Garwood, McNemar, Holm, power formula.
**Formerly [VERIFY], now fetched (2026-09-26, `AUDIT_55-56.md`):** GIoU, Soft-NMS (Gaussian applies to all boxes, no N_t), Wilson (NIST), Hungarian complexity (corrected: O(n⁴) original, O(n³) Edmonds–Karp/Tomizawa), GM-PHD update, LIF continuous form (discrete form is a training convention). Spot-verified against papers: focal (α omitted in worked numbers — flagged), DFL, HOTA (19 α), circle loss (ReID γ=128, m=0.25), TAL, Brown (OpenCV calib3d.hpp), EV100, Kalman drill (python).
