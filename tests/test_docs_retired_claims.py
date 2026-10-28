"""Doc consistency: retired claims must not resurface (docs/research/RETIRED_CLAIMS.md),
and every decimal in 60's numbers list must still be in FACTS_VERIFIED.md."""

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "docs" / "research"
REGISTRY = RESEARCH / "RETIRED_CLAIMS.md"
ALWAYS_ALLOWED = ("AUDIT_*.md", "65_DRESS_REHEARSAL.md", "RETIRED_CLAIMS.md")
# An exemption only holds when the line itself carries an explicit marker or the
# *correct* value.  Context words alone ("round 2", "h14b", "grid", "not ") are not
# enough: 77 #4 found 42 presenting round-2 3.745 as current on lines carrying them.
MARKER = re.compile(
    r"retir|supersed|pre-fix|pre-parity|historical|round 2 result|\[X\]|retract",
    re.IGNORECASE,
)
_NUM = re.compile(r"(?<![\w.])\d+(?:[.,/]\d+)*(?:\.\d+)?(?![\w])")


def _correct_values(correct: str) -> list[str]:
    """Numeric tokens of the registry's 'correct' cell (the values a line may cite)."""
    correct = re.sub(r"\([^)]*\)", " ", correct)  # parentheses hold the retired value
    return [t for t in _NUM.findall(correct) if len(t) >= 3 or "." in t or "/" in t]


# 79 / AUDIT_79: a bare "was" exempted FACTS' realism row while it still stated
# 3/14 night as current.  "was" now counts only via the correct value (below).


def is_exempt(line: str, row: dict) -> bool:
    if MARKER.search(line):
        return True
    # AUDIT_GUARD_RAILS: the registry's exemption column was parsed but never
    # consulted, so every row's qualifier cell (e.g. R65 `exempt`) was dead.  It is
    # honoured from R64 on only: older cells hold context words (R19 `round.2`)
    # that 77 #4 ruled insufficient, so enabling them would loosen those rows.
    if (
        row.get("exempt") is not None
        and int(row["id"][1:]) >= 64
        and row["exempt"].search(line)
    ):
        return True
    return any(v in line for v in row["correct_values"])


def _cell(s: str) -> str:
    s = s.strip()
    if s.startswith("`") and s.endswith("`"):
        s = s[1:-1]
    return s.replace(r"\|", "|")


def load_registry() -> list[dict]:
    rows = []
    for line in REGISTRY.read_text().splitlines():
        if not re.match(r"^\| R\d+ ", line):
            continue
        cells = re.split(r"(?<!\\)\|", line)[1:-1]
        rid, pat, correct, by, allowed, exempt = (_cell(c) for c in cells)
        rows.append(
            {
                "id": rid,
                "pattern": re.compile(pat, re.IGNORECASE),
                "correct": correct,
                "by": by,
                "allowed": [a.strip() for a in allowed.split(",") if a.strip()],
                "exempt": re.compile(exempt, re.IGNORECASE) if exempt else None,
                "correct_values": [
                    v
                    for v in _correct_values(correct)
                    if not re.search(pat, v, re.IGNORECASE)
                    and v not in re.sub(r"\\(.)", r"\1", pat)
                ],
            }
        )
    return rows


def _docs() -> list[Path]:
    return sorted((ROOT / "docs").rglob("*.md")) + [ROOT / "CLAUDE.md"]


def test_registry_parses():
    rows = load_registry()
    assert len(rows) >= 30
    assert len({r["id"] for r in rows}) == len(rows)


def test_no_retired_claims_in_docs():
    rows = load_registry()
    hits = []
    for path in _docs():
        name = path.name
        if any(fnmatch.fnmatch(name, g) for g in ALWAYS_ALLOWED):
            continue
        for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
            for r in rows:
                if any(fnmatch.fnmatch(name, g) for g in r["allowed"]):
                    continue
                if not r["pattern"].search(line):
                    continue
                if is_exempt(line, r):
                    continue
                hits.append(
                    f"{path.relative_to(ROOT)}:{n}: {r['id']} -> {r['correct']} ({r['by']})"
                )
    assert not hits, "retired claims resurfaced:\n" + "\n".join(hits)


def test_cheat_sheet_numbers_still_in_facts():
    sheet = (RESEARCH / "60_ONE_PAGE_CHEAT_SHEET.md").read_text()
    facts = (RESEARCH / "FACTS_VERIFIED.md").read_text()
    sec = re.search(r"## \d+ numbers\n(.*?)\n## ", sheet, re.DOTALL)
    assert sec, "60 has no '## N numbers' section"
    items = re.findall(r"^(\d+)\. (.*)$", sec.group(1), re.MULTILINE)
    assert len(items) >= 20
    missing = [
        f"60 item {i}: {num}"
        for i, text in items
        for num in re.findall(r"(?<![\d.])\d+\.\d+(?![\d.])", text)
        if num not in facts
    ]
    assert not missing, "60 numbers absent from FACTS_VERIFIED.md:\n" + "\n".join(missing)


# 77 #4/#13: lines that the old loose exemption let through (42 pitch / memorise
# list, 00's pointer to 58).  Each must be flagged by the tightened rule.
STALE_FIXTURES = [
    "- **H58 round 2 (use for any loiter-rule claim)** 3.745 / 0.831 … ~3,700× over",
    "Pitch: the shipped rule is 3.745 FA/cam-h and realism hit 12/14 on the tuning grid.",
    "h14b retrain lifted AP by +0.0107 over the round 2 rule",
    # AUDIT_79: bare "was" with no correct value, and an unqualified H11 night penalty.
    "Realism: 6/14 day, 3/14 `cctv_night_ir` (night was scored as usual)",
    "Night costs recall: `cctv_night_ir` degrade -0.609 (H11)",
    # AUDIT_H53: the unqualified fusion claim AUDIT_78 retired.
    "the fix is context and a second sensor",
    "context and a second sensor remove 99 % of twin FA (H53)",
    # AUDIT_81: the 0.001 FA/cam-h budget quoted as if it were a field standard.
    "the shipped rule is ~2,900× over budget",
    "every loiter rule is 4,500–87,000× over 0.001 FA/cam-h",
]
# Same claims written correctly must stay exempt.
OK_FIXTURES = [
    "~2,900× over our assumed 0.001 budget (A=4, K=500, H=8; 28 §6)",
    "val runs conf 0.001 to trace the PR tail",
    "round-3 A1 2.915 / 0.825 (round-2 3.745 superseded)",
    "realism 6/14 (12/14 was the tuning grid)",
    "h14b +0.0121 AP (the +0.0107 figure is retired: H14 label bug)",
    "night 3/13 vis, 2/13 thermal vs LLVIP (3/14 night was vs day targets)",
    "H11 -0.609 is a sensor-model sensitivity; see H32b",
    (
        "context and a second sensor remove 99 % of authorised-crosser FA (0.488 → 0.0047/cam-h, H53) at a "
        "2.3-point recall cost, all sensors simulated; a tailgater defeats it"
    ),
]


def _flagged(line: str) -> bool:
    return any(r["pattern"].search(line) and not is_exempt(line, r) for r in load_registry())


def test_stale_fixtures_flagged():
    missed = [f for f in STALE_FIXTURES if not _flagged(f)]
    assert not missed, "tightened exemption let stale lines through:\n" + "\n".join(missed)


def test_ok_fixtures_exempt():
    wrong = [f for f in OK_FIXTURES if _flagged(f)]
    assert not wrong, "correctly-marked lines flagged:\n" + "\n".join(wrong)


def test_scan_covers_engineering_docs():
    """AUDIT_13_12: docs/1*.md (12 engine notes, 13 baselines) are in the retired-claims scan."""
    names = {p.name for p in _docs()}
    assert {"13_BASELINES.md"} <= names
