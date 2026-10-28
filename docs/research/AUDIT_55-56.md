# AUDIT 55–56 · formula sheets and glossary (2026-09-26)

Method: every former **[VERIFY]** in `55` fetched and checked symbol-by-symbol; 8 further
formulas spot-checked against their papers; every worked number in `55` re-derived in
Python (numpy/scipy). 20 glossary rows in `56` checked against a primary source; unsourced
rows sourced or marked. No engine/GPU used.

**Score: 55 — 11/14 formulas correct as written, 3 corrected; 26/26 worked numbers reproduce
(1 needed a caveat). 56 — 18/20 checked rows correct, 2 refined; 2 rows could not be
sourced and are now marked [UNSOURCED]. Overall 55/60 claims correct as written (92 %).**

## 55 · formulas

| Claim | Source (fetched) | Verdict |
|---|---|---|
| GIoU = IoU − \|C\\(A∪B)\|/\|C\|, loss 1−GIoU ∈ [0,2] | Rezatofighi 2019, arXiv 1902.09630 Alg. 1 | Correct; range refined to GIoU ∈ (−1,1], loss [0,2) |
| Soft-NMS linear / Gaussian | Bodla 2017, arXiv 1704.04503 §3 | Formula correct; **imprecise**: the Gaussian applies to all b_i ∉ D with no N_t threshold — clarified |
| Hungarian "O(n³) Kuhn–Munkres" | Munkres 1957 J.SIAM 5(1); Edmonds & Karp 1972 J.ACM doi:10.1145/321694.321699; Tomizawa 1971 (via Wikipedia citations) | **Corrected**: original Kuhn/Munkres is O(n⁴); O(n³) is Edmonds–Karp/Tomizawa |
| Wilson interval | NIST/SEMATECH e-Handbook §7.2.4.1; Wilson 1927 JASA | Correct; 8/10 → [0.490, 0.943] reproduced |
| GM-PHD update | Vo & Ma 2006 IEEE TSP, author preprint eqs. 32–33 | Correct; added q(z) = N(z; Hm, R+HPHᵀ) and N̂ = ∫D |
| LIF | Gerstner, *Neuronal Dynamics* §1.3 (online) | Continuous form + hard reset added; β-discrete/soft-reset form labelled a training convention, not Gerstner |
| Focal loss γ=2, α=0.25 | Lin 2017, arXiv 1708.02002 | Formula correct; **worked numbers omit α_t** (0.00105/1.87 are γ-only; with α 0.00026/0.47) — flagged |
| DFL | GFL, arXiv 2006.04388 eq. 6 | Correct; 3.4 → 0.6/0.4 and 15 strides = 120 px reproduce |
| HOTA = mean of √(DetA·AssA) over 19 α | Luiten 2020, arXiv 2009.07736 | Correct; toy example: DetA 0.714, AssA 0.340, HOTA₀.₅ 0.493, MOTA 0.333, IDF1 0.500 reproduce; drill 2 (0.632/0.5/0.444) reproduces |
| Circle loss, γ≈128, m≈0.25 | Sun 2020, arXiv 2002.10857 eq. 6, §4 (ReID: γ=128, m=0.25) | Correct |
| TAL t = s^α u^β | TOOD, arXiv 2108.07755 | Correct; note paper uses α=1, Ultralytics α=0.5 — added |
| Brown–Conrady (OpenCV order) | OpenCV `calib3d.hpp` doc comment | Correct |
| EV100 = log₂(N²/t) − log₂(S/100) | Wikipedia "Exposure value" (ISO 2720 convention) | Correct; example 3.0 EV, blur 2.8 px, −1.22 EV / 2.33× reproduce |
| Kalman predict/update | standard; 1-D drill re-run in numpy | Correct; x=[11.833,1.167], P reproduce |

Worked numbers also re-derived (all reproduce): IoU 0.143, 0.667; COCO AP 0.686; FP/cam-h 180, 14.4 min/day; Hungarian drill optimal 5; f_x 1371 px, Identify 5.5 m, Detect 55 m; GOP 2 s, B-latency 80 ms; 43.2 GB/day, 1.30 TB, 25.9 GB; binomial SE 0.126; Clopper–Pearson [0.444, 0.975]; rule of three 0.0075, ~3,000 cam-h; power 15.7σ²/Δ² → 24.5 → 25 seeds; permutation 0.05; INT8 s=0.157, 0.079, 0.047, 3.3×; triplet 0.1; ReID AP 0.722/0.417/mAP 0.569. Not re-derived: ECE 0.105 and JPDA β (inputs live in `25`/`37`, not `55`).

IVF-PQ memory: not in `55`; `56` row "104 M vectors in 7.5 GB" = 72 B/vector, consistent with 64-byte PQ codes + 8-byte ids — arithmetic consistent, source not fetched.

## 56 · glossary

| Claim | Source | Verdict |
|---|---|---|
| NSI Gold: standards "could not confirm" | nsi.org.uk (fetched) | **Sourced**: all Gold schemes include ISO 9001, optionally 14001/45001; UKAS-accredited |
| STANAG 4609 | NGA/MISB pages CAPTCHA/403 | **Marked [UNSOURCED]** |
| DEF STAN 00-055/00-056 scope | dstan.mod.uk requires Defence Gateway login | **Marked [UNSOURCED]** |
| MOT20 ~127 people/frame | arXiv 2003.09003 Tab. 1 (127.04 train mean; 246 max) | Correct; refined |
| ByteTrack MOT17 80.3/77.3/63.1 | arXiv 2110.06864 abstract | Correct |
| BoT-SORT: CMC + ReID + KF state | arXiv 2206.14651 abstract | Correct |
| CMC (motion) | arXiv 2206.14651 | Correct |
| HOTA 19 thresholds | arXiv 2009.07736 | Correct |
| DetA / AssA definitions | arXiv 2009.07736 | Correct |
| IDF1 global bijection | arXiv 2009.07736 (review of IDF1) | Correct |
| NMS / Soft-NMS | arXiv 1704.04503 | Correct |
| DFL | arXiv 2006.04388 | Correct |
| TAL | arXiv 2108.07755 | Correct |
| PHD / GM-PHD, no labels | Vo & Ma 2006 | Correct |
| Hungarian algorithm | Munkres 1957; Edmonds–Karp 1972 | Correct; complexity added |
| LIF | Gerstner §1.3 | Correct; equation added |
| Wilson 8/10 → [0.49, 0.94] | NIST + python | Correct |
| EV100 | Wikipedia Exposure value | Correct |
| Triplet/circle/ID loss | arXiv 2002.10857 | Correct |
| Kalman filter | standard + numpy drill | Correct |

## Commits
- `fbe29c5` research 55
- `26d5500` research 56
