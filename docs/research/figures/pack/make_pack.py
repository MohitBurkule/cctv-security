"""Interview figure pack (docs/research/80_FIGURE_PACK.md).

Every plotted number is first asserted present in FACTS_VERIFIED.md (grep), so a
retired or edited FACTS value breaks this script instead of silently printing.
Run: python docs/research/figures/pack/make_pack.py
"""
import textwrap
from itertools import pairwise
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch

HERE = Path(__file__).resolve().parent
FACTS = (HERE.parents[1] / "FACTS_VERIFIED.md").read_text()


def f(token: str) -> str:
    assert token in FACTS, f"not in FACTS_VERIFIED.md: {token!r}"
    return token


plt.rcParams.update({"font.size": 15, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.titlesize": 17,
                     "figure.dpi": 150})
INK, ACC, MUTE, BAD = "#222222", "#1f5fa8", "#9a9a9a", "#b0413e"
figs = []


def caption(fig, text, width=118):
    """Hard-wrap a caption (matplotlib's wrap=True clips at the figure edge) and
    return the bottom margin it needs."""
    lines = [w for para in text.split("\n") for w in (textwrap.wrap(para, width) or [""])]
    fig.text(0.02, 0.015, "\n".join(lines), fontsize=11, color="#444", ha="left", va="bottom")
    return 0.06 + 0.026 * len(lines)


def new(title, text):
    fig, ax = plt.subplots(figsize=(11, 7.5))
    fig.suptitle(title, fontsize=20, x=0.02, ha="left", weight="bold")
    fig.subplots_adjust(bottom=max(0.2, caption(fig, text) + 0.04), top=0.88)
    return fig, ax


def box(ax, x, y, w, h, text, fc="white", ec=INK, fs=13, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.02",
                                fc=fc, ec=ec, lw=1.8))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs,
            weight="bold" if bold else "normal")


def arrow(ax, a, b, label=None):
    ax.annotate("", xy=b, xytext=a, arrowprops={"arrowstyle": "-|>", "lw": 1.8, "color": INK})
    if label:
        ax.text((a[0] + b[0]) / 2, (a[1] + b[1]) / 2 + 0.02, label, ha="center", fontsize=11, color="#444")


def blank(ax):
    ax.set_xlim(0, 1), ax.set_ylim(0, 1), ax.axis("off")


# 1 pipeline -------------------------------------------------------------------
fig, ax = new("1 · SurvSim pipeline", "Architecture per CLAUDE.md / docs/02. Truth is recorded after avoidance "
              "and boxes come from rendered masks (occlusion included).")
blank(ax)
xs = [0.01, 0.21, 0.41, 0.61, 0.81]
labels = ["Director\ntime · people\nbehaviours · PTZ", "Backend\nmock | unreal",
          "Ground truth\nMOT · parquet\nevents · calib", "Degrade\nCCTV profiles", "Eval\nFA / cam-h\ni-LIDS timing"]
for x, t in zip(xs, labels):
    box(ax, x, 0.45, 0.17, 0.3, t, fc="#eef3fa" if x == 0.01 else "white", fs=14)
for a, b in pairwise(xs):
    arrow(ax, (a + 0.17, 0.6), (b, 0.6))
ax.text(0.5, 0.25, "engine-agnostic above the backend: SI units, seeded RNG, one definition of 'visible'",
        ha="center", fontsize=13, color="#444")
figs.append(("01_pipeline", fig))

# 2 sim-to-real ----------------------------------------------------------------
fig = plt.figure(figsize=(11, 7.5))
fig.suptitle("2 · Sim-to-real: small but significant add-on gain (H51)", fontsize=20, x=0.02, ha="left", weight="bold")
a1, a2, a3 = fig.subplots(1, 3, gridspec_kw={"width_ratios": [1, 1.4, 1]})
fig.subplots_adjust(bottom=0.32, top=0.82, wspace=0.6)
caption(fig, f"H1: synthetic-only {f('0.276')} → {f('0.152')} AP, MOT20-02. H7 (2 seeds) / h14b (5 seeds):\n"
         f"synthetic added to 60 real at UNEQUAL steps: mix_100 {f('+0.0121')}, mix_300 {f('+0.0095')} over 6-epoch real-only {f('0.4862')} (grey, retired label).\n"
         f"H51 (black, 10 paired seeds, 450 steps every arm, H26 recipe exactly): real-only {f('0.4911')} [{f('0.4895')}, {f('0.4926')}]; "
         f"+100 {f('0.4953')} (gain {f('+0.0042')} [{f('+0.0024')}, {f('+0.0062')}]), +300 {f('0.4962')} (gain {f('+0.0051')} "
         f"[{f('+0.0037')}, {f('+0.0064')}]), exact sign-flip Holm p {f('0.0039')} both.\n"
         f"H26 (light blue, 5 seeds, superseded by H51): {f('+0.0041')} / {f('+0.0045')} / {f('+0.0015')} / {f('−0.0003')} at 100/300/600/1000 "
         f"over real-only {f('0.4911')}; none Holm-significant.\nH19: far synthetic-only 0.000 vs zero-shot "
         f"{f('0.613')}; +60 real frames → {f('0.817')} AP50.")
for a in (a1, a2, a3):
    a.spines[["top", "right"]].set_visible(False)
a1.bar(["zero\nshot", "synth\nonly"], [0.276, 0.152], color=[MUTE, BAD])
a1.errorbar([1], [0.152], yerr=[0.025], color=INK, capsize=5)
a1.set_title("H1 replace real", fontsize=14); a1.set_ylabel("AP, MOT20-02")
for i, v in enumerate([0.276, 0.152]):
    a1.text(i, v + 0.03, f"{v:.3f}", ha="center")
a1.set_ylim(0, 0.35)
a2.axhline(0, color=MUTE, lw=1)
a2.errorbar([100, 300], [0.0121, 0.0095], yerr=[[0.0010, 0.0011], [0.0009, 0.0011]],
            fmt="o:", color=MUTE, mfc="none", capsize=4, label="unequal steps (retired)")
h26 = [0.0041, 0.0045, 0.0015, -0.0003]
lo = [0.0012, 0.0015, -0.0020, -0.0058]; hi = [0.0071, 0.0074, 0.0049, 0.0056]
a2.errorbar([100, 300, 600, 1000], h26, yerr=[[m - l for m, l in zip(h26, lo)], [h - m for m, h in zip(h26, hi)]],
            fmt="o--", color="#a9c6e6", capsize=4, label="H26, 5 seeds (n.s.)", alpha=0.9)
h51 = [0.0042, 0.0051]
lo51 = [0.0024, 0.0037]; hi51 = [0.0062, 0.0064]
a2.errorbar([100, 300], h51, yerr=[[m - l for m, l in zip(h51, lo51)], [h - m for m, h in zip(h51, hi51)]],
            fmt="o-", color=INK, capsize=4, lw=2.5, ms=8, zorder=5, label="H51, 10 paired seeds (Holm p 0.0039)")
a2.set_xscale("log"); a2.set_xlabel("synthetic frames added"); a2.set_ylabel("Δ AP vs real-only", labelpad=2)
a2.set_title("add to 60 real", fontsize=14); a2.legend(fontsize=9, frameon=False, loc="lower left")
a3.bar(["zero\nshot", "synth\nonly", "+60\nreal"], [0.613, 0.0, 0.817], color=[MUTE, BAD, ACC])
for i, v in enumerate([0.613, 0.0, 0.817]):
    a3.text(i, v + 0.03, f"{v:.3f}", ha="center")
a3.set_title("H19 far (<60 px)", fontsize=14); a3.set_ylabel("AP50"); a3.set_ylim(0, 1)
figs.append(("02_sim_to_real", fig))

# 3 operating points -----------------------------------------------------------
fig = plt.figure(figsize=(11, 7.5))
fig.suptitle("3 · Loiter operating points: staffing picks the threshold", fontsize=20, x=0.02, ha="left", weight="bold")
ax, axb = fig.subplots(1, 2, gridspec_kw={"width_ratios": [1, 1.25]})
bot = caption(fig, f"Left: model points on H12 (58 §8.4 / H42 / H33 / H33c): A1 θ0.95 {f('2.915')} / {f('0.825')}; pooled θ0.9 "
              f"{f('5.033')} / {f('0.894')}; conformal (capped) θ{f('0.961780')} {f('2.196')} / {f('0.789')} (CRC range {f('2.10–2.22')}). "
              f"Our assumed operator budget 0.001 FA/cam-h (28 §6, A = 4 alarms/shift) is infeasible (H33 floor 0.248–0.263); "
              f"external anchor ~1 nuisance alarm/{f('zone/day')} [A] ≈ {f('0.042/h')}.\n"
              f"Right: H45c realised recall @5 min, 1 operator / 40 cams, 10 seeds, invented operator (H22): FIFO / ranked "
              f"A1 {f('0.511')} / {f('0.586')}, pooled {f('0.324')} / {f('0.504')}, conformal (capped) {f('0.584')} / {f('0.618')}; "
              f"loads 120 / 205 / {f('90.6')} alarms/h. Ship: 1 operator → conformal (capped, exact B) ranked; ≥ 2 → A1 ranked; never pooled. "
              f"Cap keys on GT identity; ID switches would reopen it (H59).")
fig.subplots_adjust(bottom=bot + 0.08, top=0.84, wspace=0.35)
for a in (ax, axb):
    a.spines[["top", "right"]].set_visible(False)
pts = [("A1 θ0.95", 2.915, 0.825, ACC), ("pooled θ0.9", 5.033, 0.894, MUTE), ("conformal\nθ0.9618 (capped)", 2.196, 0.789, INK)]
for n, x, y, c in pts:
    ax.plot(x, y, "o", ms=12, color=c)
    ax.annotate(f"{n}\n{x:g} / {y:.3f}", (x, y), xytext=(-105, {"p": -12, "A": -12, "c": -30}[n[0]]),
                textcoords="offset points", fontsize=11)
ax.set_xscale("log"); ax.set_xlim(0.0006, 12); ax.set_ylim(0.70, 0.95)
ax.axvline(0.001, color=BAD, ls=":", lw=1.5)
ax.text(0.00115, 0.705, "assumed\noperator\nbudget 0.001\n(28 §6)", color=BAD, fontsize=9, va="bottom")
ax.axvline(0.042, color="#c07a00", ls="--", lw=1.5)
ax.text(0.048, 0.705, "~1 nuisance\nalarm/zone/day\n[A] ≈ 0.042/h", color="#c07a00", fontsize=9, va="bottom")
ax.set_xlabel("false alarms per camera-hour (H12, log)"); ax.set_ylabel("model recall (actor-aware)")
ax.set_title("model", fontsize=14)
names = ["A1\nθ0.95", "pooled\nθ0.9", "conformal\nθ0.9618 (capped)"]
fifo, rank, model = [0.511, 0.324, 0.584], [0.586, 0.504, 0.618], [0.825, 0.894, 0.789]
lo_f, hi_f = [0.485, 0.304, 0.552], [0.537, 0.346, 0.616]
lo_r, hi_r = [0.554, 0.472, 0.583], [0.618, 0.535, 0.652]
xs3 = range(3)
w = 0.36
axb.bar([x - w / 2 for x in xs3], fifo, w, color=MUTE, label="FIFO",
        yerr=[[v - l for v, l in zip(fifo, lo_f)], [h - v for v, h in zip(fifo, hi_f)]], capsize=4)
axb.bar([x + w / 2 for x in xs3], rank, w, color=ACC, label="ranked",
        yerr=[[v - l for v, l in zip(rank, lo_r)], [h - v for v, h in zip(rank, hi_r)]], capsize=4)
for x, m in zip(xs3, model):
    axb.hlines(m, x - 0.4, x + 0.4, colors=INK, ls="--", lw=1.5)
axb.text(2.45, 0.80, "model\nrecall", fontsize=10, color=INK, va="center")
for x, v in zip(xs3, fifo):
    axb.text(x - w / 2, v + 0.045, f"{v:.3f}", ha="center", fontsize=10)
for x, v in zip(xs3, rank):
    axb.text(x + w / 2, v + 0.045, f"{v:.3f}", ha="center", fontsize=10, weight="bold")
axb.set_xticks(list(xs3), names, fontsize=12); axb.set_ylim(0, 1.0)
axb.set_ylabel("realised recall @5 min (1 operator)")
axb.set_title("H45 at the console", fontsize=14); axb.legend(frameon=False, loc="upper left", fontsize=11)
figs.append(("03_operating_points", fig))

# 4 alarm path -----------------------------------------------------------------
fig, ax = new("4 · Alarm path, 40-camera perimeter (74 drill 1)",
              f"Edge sizing: 10–12 cams per Orin NX with detect + ReID ({f('18× 1080p30')} decode is a ceiling). "
              "Nothing is dispatched without the operator's click; every alarm and verdict is in a WORM audit log.")
blank(ax)
box(ax, 0.01, 0.8, 0.22, 0.14, "40 fixed cameras\nsub 720p @10 fps")
box(ax, 0.30, 0.8, 0.3, 0.14, "Edge: 4 × Orin NX (+1 spare)\ndetect → track → ReID")
box(ax, 0.68, 0.8, 0.3, 0.14, "PIDS / radar / thermal\n(existing)")
box(ax, 0.25, 0.52, 0.5, 0.17, "Alarm engine (on-site)\nfuse · A1 loiter score, θ by CRC · rank queue")
box(ax, 0.2, 0.26, 0.6, 0.15, "HUMAN DECISION\ndispatch / dismiss(reason) / escalate", fc="#fbeaea", ec=BAD, bold=True)
box(ax, 0.2, 0.03, 0.6, 0.14, "Audit log (WORM)\nalarm id · clip hash · model hash · θ · operator · verdict", fs=12)
arrow(ax, (0.23, 0.87), (0.30, 0.87)); arrow(ax, (0.45, 0.8), (0.45, 0.69), "events < 1 s")
arrow(ax, (0.83, 0.8), (0.7, 0.69)); arrow(ax, (0.5, 0.52), (0.5, 0.41), "ranked queue")
arrow(ax, (0.5, 0.26), (0.5, 0.17)); ax.text(0.82, 0.32, "→ guard force", fontsize=13)
figs.append(("04_alarm_path", fig))

# 5 tracking -------------------------------------------------------------------
fig, ax = new("5 · Tracking: an appearance model helps association",
              f"MOT20 subset HOTA {f('0.443')} (TrackEval parity). H24: OSNet in ByteTrack stage 1, ΔAssA MOT20-02 "
              f"{f('+0.0139')}, batch_v8 {f('+0.0194')} (bar +0.02 not met); IDSW {f('92.6 → 87.0')} (−5.6 [−11.0, −0.2]).\n"
              "GT-box arm +0.0137 says association, not detection; synthetic *data* (H17) did not lift AssA.")
lab = ["MOT20-02\nΔAssA", "batch_v8 day\nΔAssA", "MOT20-02\nΔHOTA"]
val, lo, hi = [0.0139, 0.0194, 0.0085], [0.0018, 0.0004, None], [0.0268, 0.0439, None]
ax.bar(lab, val, color=[ACC, ACC, MUTE])
for i in range(2):
    ax.errorbar(i, val[i], yerr=[[val[i] - lo[i]], [hi[i] - val[i]]], color=INK, capsize=6)
for i, v in enumerate(val):
    ax.text(i + 0.08, v + 0.001, f"+{v:.4f}", fontsize=13)
ax.axhline(0.02, color=BAD, ls=":"); ax.text(2.3, 0.0205, "pre-registered bar +0.02", color=BAD, fontsize=11, ha="right")
ax.text(1.6, 0.036, "ID switches MOT20-02\n92.6 → 87.0", fontsize=14, weight="bold")
ax.text(1.6, 0.03, f"baseline HOTA {0.443}", fontsize=13, color="#444")
ax.set_ylabel("gain from appearance cue"); ax.set_ylim(0, 0.046)
figs.append(("05_tracking", fig))

# 6 night ----------------------------------------------------------------------
fig, ax = new("6 · Night: the renders are not night-realistic yet",
              f"H32a: raw renders {f('3/13 visible · 2/13 thermal')} statistics in band vs LLVIP; tuned profiles overfit "
              "(9/13 → 2/13, 10/13 → 3/13 hold-out).\nH32b: with no profile in band, the recall drops "
              f"(IR {f('−0.565')}, lowlight {f('−0.835')}, thermal {f('−0.470')}) measure the degrade model, so no recall is a night-penalty estimate.")
ax.barh(["visible", "thermal"], [3, 2], color=ACC, label="raw render in band")
ax.barh(["visible", "thermal"], [10, 11], left=[3, 2], color="#e4e4e4", label="out of band")
for y, v in enumerate([3, 2]):
    ax.text(v + 0.2, y, f"{v}/13", va="center", fontsize=15, weight="bold")
ax.set_xlim(0, 13); ax.set_xlabel("image statistics in LLVIP band (of 13)"); ax.legend(frameon=False, loc="lower right")
figs.append(("06_night", fig))

# 7 edge -----------------------------------------------------------------------
fig, (b1, b2) = plt.subplots(1, 2, figsize=(11, 7.5))
fig.suptitle("7 · Edge budget: decode is a ceiling, INT8 is not free", fontsize=20, x=0.02, ha="left", weight="bold")
bot = caption(fig, f"Orin NX 16 GB: {f('18× 1080p30')} H.265 decode is a ceiling; {f('~10–12 cams/NX')} for detect 640 @10 fps + ReID "
         "(plan figure, ReID scaling [A]) → 4 NX for 40 cams.\n"
         f"H38 (yolov8n, MOT20-02 AP, 3 seeds): FP16 loss {f('0.0000')}; INT8 static PTQ loss {f('0.0117')} "
         "(range 0.0081..0.0154; bar 0.015 not met, AP75 −0.030).")
fig.subplots_adjust(bottom=bot + 0.08, top=0.84, wspace=0.4)
for a in (b1, b2):
    a.spines[["top", "right"]].set_visible(False)
b1.bar(["decode\nceiling", "working\n(detect+ReID)"], [18, 11], yerr=[[0, 1], [0, 1]], color=[MUTE, ACC], capsize=6)
b1.text(0, 18.4, "18", ha="center", fontsize=15); b1.text(1, 12.4, "10–12", ha="center", fontsize=15)
b1.set_ylabel("cameras per Orin NX"); b1.set_ylim(0, 21)
b2.bar(["FP16", "INT8"], [0.0, 0.0117], yerr=[[0, 0.0036], [0.0003, 0.0037]], color=[ACC, BAD], capsize=6)
b2.axhline(0.015, color=BAD, ls=":"); b2.text(-0.4, 0.0153, "loss bar 0.015", color=BAD, fontsize=11)
b2.text(0, 0.0008, "0.0000", ha="center", fontsize=14); b2.text(1, 0.0125, "−0.012 AP", ha="center", fontsize=14, weight="bold")
b2.set_ylabel("AP loss vs FP32"); b2.set_ylim(0, 0.02)
figs.append(("07_edge_budget", fig))

# 8 drift ----------------------------------------------------------------------
fig, ax = new("8 · Drift monitor: textbook tests fire all the time",
              f"H34 (9 cams × 12 injected shifts, 1-s windows): PSI and KS fire on 100 % of stationary windows = {f('1,440 FA/24 cam-h')}; "
              f"calibrated z detects {f('6/12')} at {f('9.2 FA/24 cam-h')}.\nEmbedding arm: 0 null fires but 0/12 detected. "
              "Verdict INCONCLUSIVE under the pre-registered rule.\n"
              f"1,440 assumes {f('one evaluation per minute')} (1,440 min/day); at the 1-s window rate it would be 60× higher.")
ax.bar(["PSI / KS", "calibrated z", "embedding"], [1440, 9.2, 0.0], color=[BAD, ACC, MUTE])
ax.set_yscale("symlog", linthresh=10)
for i, (v, d) in enumerate([(1440, "detects: n/a (always on)"), (9.2, "detects 6/12"), (0, "detects 0/12")]):
    ax.text(i, max(v, 0.5) * 1.3, f"{v:g} FA/24 cam-h\n{d}", ha="center", fontsize=13)
ax.set_ylabel("false triggers per 24 camera-hours"); ax.set_ylim(0, 8000)
figs.append(("08_drift", fig))

# 9 line-crossing ---------------------------------------------------------------
fig = plt.figure(figsize=(11, 7.5))
fig.suptitle("9 · Line-crossing: rule → twins → fusion", fontsize=20, x=0.02, ha="left", weight="bold")
c1, c2 = fig.subplots(1, 2, gridspec_kw={"width_ratios": [1, 1.25]})
bot = caption(fig, f"H40 (old unfenced worlds, assumed tracker noise): naive {f('70.96')} → gated {f('4.20')} FA/cam-h; recall C 0.100.\n"
              f"H40b (fenced worlds, 3,002 clean cam-h): arm C non-twin FA 0 (rule of three ≤ 0.001), but authorised twins "
              f"(patrol + maintenance) {f('0.488')} FA/cam-h; recall@10 {f('0.782')}.\n"
              f"H53 late fusion (gate log + BLE tag + PIDS): twins → {f('0.0047')} FA/cam-h (99 % removed), recall {f('0.782 → 0.758')}. "
              "ALL sensors simulated, parameters assumed, matched on TRUE positions.\n"
              f"A tailgater defeats the gate log: tailgate recall {f('0.007')} combined.")
fig.subplots_adjust(bottom=bot + 0.08, top=0.84, wspace=0.45)
for a in (c1, c2):
    a.spines[["top", "right"]].set_visible(False)
lab9 = ["H40\nnaive", "H40\ngated", "H40b C\ntwins", "H53\nfused"]
v9 = [70.96, 4.20, 0.488, 0.0047]
c1.bar(lab9, v9, color=[BAD, MUTE, "#c07a00", ACC])
c1.set_yscale("log"); c1.set_ylim(0.001, 300)
for i, v in enumerate(v9):
    c1.text(i, v * 1.4, f"{v:g}", ha="center", fontsize=12, weight="bold")
c1.axvline(1.5, color=INK, ls=":", lw=1)
c1.text(0.5, 0.0016, "old worlds", ha="center", fontsize=10, color="#444")
c1.text(2.5, 0.0016, "fenced worlds", ha="center", fontsize=10, color="#444")
c1.set_ylabel("false alarms per camera-hour (log)"); c1.set_title("false alarms", fontsize=14)
lab9b = ["H40b C", "H53 fused", "tailgater\n(fused)"]
r9 = [0.782, 0.758, 0.007]
c2.bar(lab9b, r9, color=[MUTE, ACC, BAD],
       yerr=[[0.782 - 0.736, 0.758 - 0.710, 0], [0.829 - 0.782, 0.805 - 0.758, 0]], capsize=5)
for i, v in enumerate(r9):
    c2.text(i + 0.22, v + 0.02, f"{v:.3f}", fontsize=12, weight="bold")
c2.axhline(0.9, color=BAD, ls=":"); c2.text(2.4, 0.91, "recall bar 0.9", color=BAD, fontsize=10, ha="right")
c2.set_ylim(0, 1.0); c2.set_ylabel("recall@10 s (actor-aware)"); c2.set_title("recall", fontsize=14)
figs.append(("09_line_crossing", fig))

# 10 evasion -------------------------------------------------------------------
fig, ax = new("10 · Evasion: crowd cover hurts, clothing does not (H47)",
              f"H47: YOLO26n zero-shot recall vs matched control (0.948), 2 cams × 2–3 seeds, 30 s clips; clip-cluster 95 % CIs (AUDIT_H47): "
              f"crowd_cover {f('−0.201 [−0.254, −0.154]')}, wall_hugging {f('−0.054 [−0.074, −0.033]')} (43 % fewer ≥ 20 px frames), "
              f"slow {f('+0.036 [+0.015, +0.061]')}; dark / hi-vis / hood (colour proxy) |Δ| ≤ 0.003. Not met (1/6). "
              "Only 4 clips per technique, so min clip-level p = 1/16.\n"
              "UNTESTED (no CC0 asset): umbrella, carried object, crouch/crawl, face-away.")
tech = ["crowd\ncover", "wall\nhugging", "dark\nclothing", "hi-vis", "hood\n(colour proxy)", "slow"]
d = [-0.201, -0.054, 0.0027, 0.0013, -0.0012, 0.036]
lo10 = [-0.254, -0.074, None, None, None, 0.015]; hi10 = [-0.154, -0.033, None, None, None, 0.061]
ax.bar(tech, d, color=[BAD, BAD, MUTE, MUTE, MUTE, ACC])
for i in range(6):
    if lo10[i] is not None:
        ax.errorbar(i, d[i], yerr=[[d[i] - lo10[i]], [hi10[i] - d[i]]], color=INK, capsize=6)
    ax.text(i, (hi10[i] if hi10[i] is not None else d[i]) + 0.012 if d[i] >= -0.01 else (lo10[i] - 0.03),
            f"{d[i]:+.3f}" if abs(d[i]) > 0.01 else "≈ 0", ha="center", fontsize=12, weight="bold")
ax.axhline(0, color=INK, lw=1)
ax.set_ylim(-0.3, 0.1); ax.set_ylabel("Δ recall vs matched control (YOLO26n)")
figs.append(("10_evasion", fig))

with PdfPages(HERE / "pack.pdf") as pdf:
    for name, fg in figs:
        fg.savefig(HERE / f"{name}.png", dpi=150)
        pdf.savefig(fg)
print("wrote", len(figs), "figures to", HERE)
