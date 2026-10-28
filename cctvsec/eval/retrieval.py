"""Natural-language search over recorded events.

"Show me the man in the red jacket who was loitering near gate B after ten" is
what an operator actually wants, and it is the capability the vendor describes for
media monitoring. The hard part is not the language: it is that the answer must
be *checkable*, and on real footage nobody knows the true answer, so retrieval
systems are usually demonstrated rather than measured.

Here the truth is known exactly — every event, identity, appearance epoch and
zone is recorded — so a query can be scored properly with recall@k and mean
reciprocal rank against a ground-truth answer set.

The parser is deliberately a structured one rather than an embedding model. Three
reasons:

1. It is **auditable**. An operator can see that "after 22:00" became a time
   filter, which matters when a search result is used to justify an intervention.
2. It gives an honest **floor**. A VLM that cannot beat explicit attribute
   matching on attribute queries is not earning its inference cost, and that
   comparison is only possible if the floor exists.
3. It **fails visibly**. Unparsed terms are reported rather than silently ignored,
   so a query that asked for something the index cannot express says so instead of
   returning confident nonsense.

What it cannot do is the open-vocabulary part — "acting strangely", "looks
nervous" — which is exactly where a language model earns its place. Those terms
land in `unparsed` rather than being quietly dropped.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from typing import Any

# Colour words mapped to representative hues, so "red jacket" can match a hex.
COLOUR_TERMS: dict[str, tuple[int, int, int]] = {
    "red": (200, 30, 30), "blue": (30, 60, 200), "green": (40, 160, 60),
    "yellow": (230, 210, 40), "orange": (235, 140, 30), "purple": (130, 50, 170),
    "pink": (235, 120, 180), "brown": (120, 80, 40), "grey": (128, 128, 128),
    "gray": (128, 128, 128), "black": (25, 25, 25), "white": (235, 235, 235),
}

GARMENT_TERMS = ("jacket", "coat", "hoodie", "shirt", "tshirt", "t-shirt", "top",
                 "trousers", "jeans", "shorts", "cap", "hat", "hood", "vest",
                 "mask", "backpack", "bag", "suitcase", "helmet")

BEHAVIOUR_TERMS: dict[str, str] = {
    "loiter": "loiter", "loitering": "loiter", "hanging around": "loiter",
    "waiting": "commute_wait", "fight": "fight", "fighting": "fight",
    "argument": "argument", "arguing": "argument",
    "tamper": "tamper", "tampering": "tamper",
    "abandon": "abandon", "abandoned": "abandon", "left a bag": "abandon",
    "following": "follow", "follow": "follow",
    "running": "flee", "fleeing": "flee", "ran": "flee",
    "theft": "theft", "stealing": "theft", "snatch": "theft",
    "intrusion": "intrusion", "trespass": "intrusion",
    "recon": "recon", "reconnaissance": "recon", "casing": "recon",
    "collapsed": "person_down", "fell": "person_down", "person down": "person_down",
}


@dataclass
class Query:
    """A parsed query. Every field is optional; unset means unconstrained."""

    raw: str
    behaviour: str | None = None
    colour: str | None = None
    garment: str | None = None
    zone: str | None = None
    after_s: float | None = None
    before_s: float | None = None
    min_duration_s: float | None = None
    unparsed: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {"raw": self.raw, "behaviour": self.behaviour, "colour": self.colour,
                "garment": self.garment, "zone": self.zone,
                "after_s": self.after_s, "before_s": self.before_s,
                "min_duration_s": self.min_duration_s, "unparsed": self.unparsed}

    @property
    def is_empty(self) -> bool:
        """True when nothing in the text became a filter."""
        return not any((self.behaviour, self.colour, self.garment, self.zone,
                        self.after_s, self.before_s, self.min_duration_s))

    @property
    def understood(self) -> bool:
        """Whether the query can be answered at all by this index."""
        return not self.is_empty

    def explain(self) -> str:
        """Plain-language account of what the query became, for the operator."""
        if self.is_empty:
            return ("nothing in this query maps to an indexed attribute"
                    + (f"; unrecognised: {', '.join(self.unparsed)}" if self.unparsed else ""))
        parts = []
        for name, value in (("behaviour", self.behaviour), ("colour", self.colour),
                            ("garment", self.garment), ("zone", self.zone)):
            if value:
                parts.append(f"{name}={value}")
        if self.after_s is not None:
            parts.append(f"after {int(self.after_s // 3600):02d}:00")
        if self.before_s is not None:
            parts.append(f"before {int(self.before_s // 3600):02d}:00")
        if self.min_duration_s is not None:
            parts.append(f"lasting >= {self.min_duration_s:.0f}s")
        note = f"; ignored: {', '.join(self.unparsed)}" if self.unparsed else ""
        return ", ".join(parts) + note


def _clock_to_seconds(text: str) -> float | None:
    """Parse '22:00', '10pm', '9.30am' into seconds past midnight."""
    m = re.match(r"^(\d{1,2})[:.](\d{2})\s*(am|pm)?$", text)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
    else:
        m = re.match(r"^(\d{1,2})\s*(am|pm)$", text)
        if not m:
            return None
        hour, minute = int(m.group(1)), 0
    meridiem = m.group(3) if m.lastindex and m.lastindex >= 3 else m.group(2)
    if meridiem == "pm" and hour < 12:
        hour += 12
    elif meridiem == "am" and hour == 12:
        hour = 0
    return float(hour * 3600 + minute * 60)


def parse(text: str, zones: Sequence[str] = ()) -> Query:
    """Turn a natural-language request into explicit filters."""
    q = Query(raw=text)
    lowered = text.lower()
    consumed: list[str] = []

    for phrase, canonical in sorted(BEHAVIOUR_TERMS.items(), key=lambda kv: -len(kv[0])):
        if phrase in lowered and q.behaviour is None:
            q.behaviour = canonical
            consumed.append(phrase)

    for word in COLOUR_TERMS:
        if re.search(rf"\b{word}\b", lowered) and q.colour is None:
            q.colour = word
            consumed.append(word)

    for word in GARMENT_TERMS:
        if re.search(rf"\b{re.escape(word)}\b", lowered) and q.garment is None:
            q.garment = word
            consumed.append(word)

    # Zones are matched on their trailing token so "gate B" finds "zone.gate_b".
    for zone in zones:
        tail = zone.split(".")[-1].replace("_", " ").lower()
        if tail and tail in lowered:
            q.zone = zone
            consumed.append(tail)
            break

    for keyword, attr in (("after", "after_s"), ("before", "before_s")):
        m = re.search(rf"{keyword}\s+(\d{{1,2}}[:.]\d{{2}}\s*(?:am|pm)?|\d{{1,2}}\s*(?:am|pm))",
                      lowered)
        if m:
            seconds = _clock_to_seconds(m.group(1).strip())
            if seconds is not None:
                setattr(q, attr, seconds)
                consumed.append(m.group(0))

    m = re.search(r"(?:more than|over|longer than|at least)\s+(\d+)\s*(second|minute)", lowered)
    if m:
        q.min_duration_s = float(m.group(1)) * (60.0 if "minute" in m.group(2) else 1.0)
        consumed.append(m.group(0))

    # Anything meaningful we did not understand is reported, never dropped.
    stop = {"the", "a", "an", "who", "was", "is", "in", "at", "near", "by", "me",
            "show", "find", "someone", "person", "man", "woman", "with", "of",
            "and", "to", "from", "on", "for", "wearing", "any", "all"}
    remaining = lowered
    for phrase in consumed:
        remaining = remaining.replace(phrase, " ")
    q.unparsed = [w for w in re.findall(r"[a-z']{3,}", remaining) if w not in stop]
    return q


# ------------------------------------------------------------------- index


@dataclass
class IndexedEvent:
    """One event with the attributes needed to answer a query."""

    event_id: str
    uid: str
    label: str
    t_start: float
    t_end: float
    zone: str | None = None
    colour: str | None = None
    garments: tuple[str, ...] = ()
    clock_s: float | None = None        # time of day, if the scenario has one

    @property
    def duration_s(self) -> float:
        return max(self.t_end - self.t_start, 0.0)


def build_index(
    events: Iterable[dict[str, Any]],
    identities: Iterable[dict[str, Any]] = (),
    day_start_s: float = 0.0,
) -> list[IndexedEvent]:
    """Join events to the appearance in force when they happened.

    Appearance is joined *per epoch*, not per person: someone who changed jacket
    halfway through must match "red jacket" only for the part of the timeline when
    they were actually wearing it.
    """
    epochs: dict[str, list[dict[str, Any]]] = {}
    for row in identities:
        epochs.setdefault(str(row.get("uid")), []).append(row)

    out: list[IndexedEvent] = []
    for ev in events:
        uid = str((ev.get("actors") or [None])[0] or ev.get("uid") or "")
        t0 = float(ev.get("t_start", 0.0))
        t1 = float(ev.get("t_end") or t0)

        colour, garments = None, ()
        for row in epochs.get(uid, []):
            t_from = float(row.get("t_from", 0.0))
            t_to = float(row.get("t_to") if row.get("t_to") is not None else 1e12)
            if t_from <= t0 < t_to:
                colour = row.get("dominant_colour")
                outfit = row.get("outfit")
                if isinstance(outfit, str):
                    import json
                    try:
                        outfit = json.loads(outfit)
                    except ValueError:
                        outfit = {}
                if isinstance(outfit, dict):
                    garments = tuple(str(v) for k, v in outfit.items()
                                     if k in ("top", "outer", "bottom", "headwear") and v)
                break

        out.append(IndexedEvent(
            event_id=str(ev.get("event_id", f"e{len(out)}")), uid=uid,
            label=str(ev.get("label", "")), t_start=t0, t_end=t1,
            zone=ev.get("zone"), colour=colour, garments=garments,
            clock_s=day_start_s + t0 if day_start_s else None,
        ))
    return out


def _colour_matches(query_colour: str, hex_colour: str | None) -> bool:
    if not hex_colour:
        return False
    try:
        v = hex_colour.lstrip("#")
        rgb = (int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16))
    except (ValueError, IndexError):
        return False
    target = COLOUR_TERMS[query_colour]
    # Euclidean distance in RGB is crude but predictable, and an operator can be
    # told the rule. A perceptual space would match better and explain worse.
    distance = sum((a - b) ** 2 for a, b in zip(rgb, target)) ** 0.5
    return distance < 110.0


def search(query: Query, index: Sequence[IndexedEvent]) -> list[tuple[IndexedEvent, float]]:
    """Return matching events, best first, with a transparent score.

    A query the parser could not turn into a single filter returns **nothing**.
    The tempting alternative — treating "no filters" as "match everything" — hands
    back the whole index ranked by duration, which reads as a confident answer to
    a question that was never understood. "Someone acting shifty" must come back
    empty with the unparsed terms listed, so the operator knows to rephrase.
    """
    if query.is_empty:
        return []

    results: list[tuple[IndexedEvent, float]] = []
    for ev in index:
        score, matched = 0.0, 0
        if query.behaviour:
            if query.behaviour not in ev.label:
                continue
            score += 2.0
            matched += 1
        if query.zone:
            if ev.zone != query.zone:
                continue
            score += 1.5
            matched += 1
        if query.min_duration_s is not None:
            if ev.duration_s < query.min_duration_s:
                continue
            score += 1.0
            matched += 1
        if query.after_s is not None:
            clock = ev.clock_s if ev.clock_s is not None else ev.t_start
            if clock < query.after_s:
                continue
            score += 1.0
            matched += 1
        if query.before_s is not None:
            clock = ev.clock_s if ev.clock_s is not None else ev.t_start
            if clock > query.before_s:
                continue
            score += 1.0
            matched += 1
        if query.colour:
            if not _colour_matches(query.colour, ev.colour):
                continue
            score += 1.5
            matched += 1
        if query.garment:
            garment = query.garment.replace("-", "")
            if not any(garment in g.lower().replace("_", "") for g in ev.garments):
                continue
            score += 1.0
            matched += 1

        if matched:
            # Longer events rank higher among equals: an operator asking about
            # loitering wants the twenty-minute dwell, not a four-second blip.
            results.append((ev, score + min(ev.duration_s / 600.0, 0.5)))

    results.sort(key=lambda kv: -kv[1])
    return results


# -------------------------------------------------------------- evaluation


def evaluate_queries(
    cases: Sequence[tuple[str, set[str]]],
    index: Sequence[IndexedEvent],
    zones: Sequence[str] = (),
    k: int = 5,
) -> dict[str, Any]:
    """Score queries against known answers with recall@k and MRR."""
    recalls: list[float] = []
    reciprocal: list[float] = []
    per_query: list[dict[str, Any]] = []

    for text, expected in cases:
        q = parse(text, zones)
        hits = [ev.event_id for ev, _ in search(q, index)]
        top = hits[:k]
        found = expected & set(top)
        recall = len(found) / len(expected) if expected else 0.0

        rank = next((i + 1 for i, h in enumerate(hits) if h in expected), None)
        recalls.append(recall)
        reciprocal.append(1.0 / rank if rank else 0.0)
        per_query.append({
            "query": text, "parsed": q.as_dict(), "returned": len(hits),
            f"recall@{k}": round(recall, 3),
            "first_hit_rank": rank, "unparsed_terms": q.unparsed,
        })

    return {
        f"recall@{k}": round(sum(recalls) / len(recalls), 4) if recalls else 0.0,
        "mrr": round(sum(reciprocal) / len(reciprocal), 4) if reciprocal else 0.0,
        "n_queries": len(cases),
        "per_query": per_query,
    }
