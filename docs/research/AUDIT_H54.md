# AUDIT_H54 · Fence-gate tailgate + estimated-position fusion

Audited 2026-09-27 against `out/experiments/h54_tailgate_fusion/results.json`,
`survsim/experiments/sensor_fusion.py` (`fuse_world_h54`), config `h54_tailgate_fusion.yaml`,
`survsim/director/behaviours.py` (`FenceTailgate`, `StaffEscort`), pre-registration `137a338`
(32 §H54), runner `b2e71e0`, results `6e6993f`. No GPU, nothing re-run; recomputed from the JSON.

**Score: 86 → 100** (every headline number matched; four imprecise claims corrected; the benign-noise
upper bound and three design caveats made explicit wherever H54 is quoted).

## 1. Numbers recomputed (all match)

| claim | recomputed | ok |
|---|---|---|
| est C+abc 99.1 % [98.6, 99.5], 2,064 → 19 / 3,002 cam-h | est 19 alarms, 0.9908 [0.9860, 0.9950] | ✓ |
| true C+abc 99.1 % [98.7, 99.5] | **18** alarms, 0.9913 [0.9869, 0.9951] — not 19 | ✓ (see corr. 1) |
| recall@10 0.782 → 0.772, 3 detections, both matchings | 233 → 230 of 298 in `true_` and `est_` | ✓ |
| 100 tailgate worlds, 89 truth events, median gap 3.0 s | 100 / 89 / 86 logged; median of 86 gaps 3.0 s, max 46.6; 12 > 10 s | ✓ |
| C+abc 0.056 vs C+abcg 0.685 [0.589, 0.778] | 5/89; 61/89, boot [0.589, 0.778] (both matchings) | ✓ |
| counter costs removal 99.1 → 96.3 % | est C+abcg 76 alarms, 0.9632 [0.9529, 0.9732]; +0.019 FA/cam-h; staff pairs 0.0083 | ✓ |
| stolen tag 0.674 / 0.698 | 201 / 208 of 298 | ✓ |
| C reproduces H40b | C recall 0.782 (233/298) as H40b/H53; C twin FA 0.688 = H53's 0.488 + staff pairs 0.196 | ✓ |
| est vs true ≤ 0.3 pt on every arm | max gap C+a 98.69 vs 98.45 = 0.24 pt | ✓ |
| decision (four legs) | `removal_ge_0.90`, `recall_loss_le_0.03`, `tailgate_gate_ge_0.6`, `tailgate_nogate_lt_0.6` all true | ✓ |

## 2. Design checks

* **Principle 1 (fence_tailgate GT)** — the `tailgate` record is written in `FenceTailgate.step` at the
  tick the follower's *actual* position first lies inside the component, with `t_follower` = that tick;
  `t_leader` is the tick the tailgater observed the authorised leader inside within 3.5 m of the gate
  (actual state, ±1 tick); gap = difference. Truth for recall is the first tick of the true track inside
  a sterile zone after the hostile phase starts. ✓ Caveats: 3 of 89 truth events have no logged record
  (not diagnosed); 12 of 86 gaps exceed 10 s (the follow walk can stall), so "within seconds" is the median.
* **Every sensor/counter parameter is an assumption** — gate log, RF, PIDS carried over from H53's declared
  list; counter p 0.95, ±10 s excess window and the 3 m gate radius are in the pre-reg ("ASSUMPTION", "> 3 m
  from every gate") and in the config block `# simulated sensors: ASSUMPTIONS, not fitted`. ✓ Two
  unregistered details: the counter counts only twins' and incident actors' passages (never commuters or
  wildlife — idealised), and the excess trigger is associated with PIDS's [−30, +5] s window.
* **Estimated matching** uses the alarmed noisy track's own last outside→inside transition and position.
  ✓ But the noise model (H40b: 0.30 m jitter, fragmentation, ghosts) **never swaps identity between two
  people**. Fragmentation starts a new track for the same person; it never hands the staff escort's track
  to the tailgater. So "estimated matching costs nothing" is a property of the noise model: **99.1 % is an
  upper bound under a benign noise model**, and the pre-registered ≈ 90 % prediction was wrong in the
  optimistic direction. H24 measured ByteTrack+OSNet IDSW at 87.0–92.6 per MOT20-02 run — H59 (66).

## 3. Corrections (Edit in place)

| # | where | was | now |
|---|---|---|---|
| 1 | 32 §H54 decision | "19 of 2,064" read as both matchings | true matching leaves 18 |
| 2 | 32 §H54 Reading (1), 66, FACTS | "costs almost nothing"; "prediction was wrong" | upper bound under a no-IDSW noise model; wrong in the optimistic direction |
| 3 | 32 §H54 Reading | "follows through within seconds" implicit | median 3.0 s, 12/86 > 10 s, 3 events unlogged |
| 4 | 32 §H54 Reading | counter "counts every inward passage" | counts only twins + incident actors; window = PIDS's |

## 4. Fold-in

FACTS H54 row qualified + audit row; 52/64 register rows, 52 hard-negatives bullet, 64 H54 paragraph;
60 item 40; 48 C8 follow-up 4 + weak line; 65 v2 §2 item 4, §7, §10; 74 drill 1 (gate counter drawn as a
sensor); 76 row; 78 §1.5 and opener; 66 H54 audit line + new H59 (fusion under H24-calibrated ID switches and
track breaks); 00 index.

**78 opener, final form:** "context and a second sensor remove 99 % of authorised-crosser FA (0.488 →
0.0047/cam-h, H53) at a 2.3-point recall cost, all sensors simulated; a tailgater defeats it unless a gate
people-counter is added (0.685 recall, H54)." RETIRED_CLAIMS R55's allowed form extended to match (the
regex still requires H53 + simulated + tailgat). Both doc tests pass.
