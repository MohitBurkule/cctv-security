"""WORM-style evidence log (docs/research/86 §4, §7 ``log_entry``; H60).

Append-only JSONL; each record carries ``prev_hash`` and
``entry_hash = sha256(prev_hash || canonical_json(record without entry_hash))``.
Editing, deleting or reordering any record breaks :func:`verify` at that index.
Operator ids are stored only as a salted sha256. This is tamper-*evident*, not
tamper-proof: real WORM needs write-once storage or an external anchor for the head.

Slice 2 (32 §H60 slice 2): the canonical form is RFC 8785 (JCS)-compatible for the JSON
subset cards and records use; :func:`write_pack` writes ``head.json`` (chain head, record
count, created_at) and :func:`verify` requires a head by default, so tail truncation and a
full re-chain from genesis fail closed. ``head.json`` beside the log only helps if a copy
of the head is also anchored out of band (the CLI prints it for that); an attacker who can
rewrite the log can rewrite ``head.json`` too.
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from decimal import Decimal
from pathlib import Path

GENESIS = "0" * 64
#: public, shared by every install -- test/sim use only (the CLI refuses it in mode=real).
DEFAULT_SALT = "survsim-h60"
VERDICTS = frozenset({"dispatch", "dismiss", "escalate", "bulk_ack"})


def _jcs_number(x: float) -> str:
    """ECMAScript Number::toString of the shortest round-trip repr (RFC 8785 §3.2.2.3)."""
    if isinstance(x, int):
        return str(x)
    if math.isnan(x) or math.isinf(x):
        raise ValueError("NaN/Infinity are not JSON (RFC 8785 refuses them)")
    if x == 0:
        return "0"  # -0 serialises as 0
    _sign, digs, exp = Decimal(repr(abs(x))).as_tuple()
    d = "".join(map(str, digs)).rstrip("0") or "0"
    k = len(d)
    n = len(digs) + int(exp)  # ES "n": decimal-point position relative to d
    neg = "-" if x < 0 else ""
    if k <= n <= 21:
        out = d + "0" * (n - k)
    elif 0 < n <= 21:
        out = d[:n] + "." + d[n:]
    elif -6 < n <= 0:
        out = "0." + "0" * (-n) + d
    else:
        e = n - 1
        out = (d if k == 1 else d[0] + "." + d[1:]) + "e" + ("+" if e > 0 else "-") + str(abs(e))
    return neg + out


def _jcs(v) -> str:
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, (int, float)):
        return _jcs_number(v)
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    if isinstance(v, (list, tuple)):
        return "[" + ",".join(_jcs(x) for x in v) + "]"
    if isinstance(v, dict):
        if not all(isinstance(k, str) for k in v):
            raise TypeError("JSON object keys must be strings")
        ks = sorted(v, key=lambda k: k.encode("utf-16-be"))  # UTF-16 code-unit order
        return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + _jcs(v[k]) for k in ks) + "}"
    raise TypeError(f"not JSON-serialisable: {type(v).__name__}")


def canonical(rec) -> bytes:
    """RFC 8785 (JCS)-compatible UTF-8 bytes for the subset used here: sorted keys (UTF-16
    order), no whitespace, integers as-is, floats as ECMAScript shortest round-trip, strings
    with JSON's minimal escapes; NaN/Infinity refused."""
    return _jcs(rec).encode("utf-8")


_canon = canonical  # slice-1 name


def hash_operator(operator_id: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}|{operator_id}".encode()).hexdigest()


def card_sha256(card: dict) -> str:
    return hashlib.sha256(_canon(card)).hexdigest()


def make_entry(prev_hash: str, card: dict, operator_id: str, salt: str, verdict: str,
               t_verdict: float, reason: str | None = None) -> dict:
    if verdict not in VERDICTS:
        raise ValueError(f"verdict must be one of {sorted(VERDICTS)}, got {verdict!r}")
    if verdict == "dismiss" and not reason:
        raise ValueError("dismiss needs a reason code")
    rec = {
        "alarm_id": card["alarm_id"], "card_sha256": card_sha256(card),
        "operator_id_hash": hash_operator(operator_id, salt), "verdict": verdict,
        "reason_code": reason, "t_verdict": t_verdict,
        "time_to_verdict_s": round(t_verdict - float(card["t"]), 3), "prev_hash": prev_hash,
    }
    rec["entry_hash"] = hashlib.sha256(prev_hash.encode() + _canon(rec)).hexdigest()
    return rec


def write_log(path: Path, entries: list[dict]) -> str:
    Path(path).write_text("".join(json.dumps(e, sort_keys=True) + "\n" for e in entries))
    return entries[-1]["entry_hash"] if entries else GENESIS


def write_pack(out_dir: Path, entries: list[dict], created_at: float | None = None) -> dict:
    """Write ``evidence_log.jsonl`` + ``head.json``; returns the head record."""
    out_dir = Path(out_dir)
    h = write_log(out_dir / "evidence_log.jsonl", entries)
    head = {"chain_head": h, "n_records": len(entries),
            "created_at": time.time() if created_at is None else created_at}
    (out_dir / "head.json").write_text(json.dumps(head, indent=1, sort_keys=True))
    return head


def chain(cards: list[dict], decisions: list[tuple[str, str | None, float]],
          operator_id: str, salt: str) -> list[dict]:
    """Chain one entry per (card, (verdict, reason, t_verdict))."""
    out, prev = [], GENESIS
    for card, (v, r, tv) in zip(cards, decisions, strict=True):
        e = make_entry(prev, card, operator_id, salt, v, tv, r)
        out.append(e)
        prev = e["entry_hash"]
    return out


def verify_cards(path_or_entries, cards) -> tuple[bool, str | None]:
    """Bind cards.jsonl to the log: every card must have exactly one record whose
    ``card_sha256`` equals the card's recomputed canonical hash, and vice versa.

    Returns (ok, offending alarm_id or None). Run :func:`verify` for the chain itself.
    """
    if isinstance(path_or_entries, (str, Path)):
        entries = [json.loads(x) for x in Path(path_or_entries).read_text().splitlines() if x.strip()]
    else:
        entries = list(path_or_entries)
    if isinstance(cards, (str, Path)):
        cards = [json.loads(x) for x in Path(cards).read_text().splitlines() if x.strip()]
    logged = {}
    for e in entries:
        logged.setdefault(e.get("alarm_id"), []).append(e.get("card_sha256"))
    seen = set()
    for c in cards:
        aid = c.get("alarm_id")
        if aid in seen or logged.get(aid) != [card_sha256(c)]:
            return False, aid
        seen.add(aid)
    extra = set(logged) - seen
    if extra:
        return False, min(str(x) for x in extra)
    return True, None


def verify(path_or_entries, expected_head: str | None = None, *, head: dict | Path | None = None,
           require_head: bool = True) -> tuple[bool, int | None]:
    """(ok, index of first bad record or None). Fails closed on a missing head.

    The head is ``expected_head`` if given, else ``head`` (a head.json dict or path), else
    ``head.json`` beside a log path. With ``require_head`` (default) no head => fail at
    ``len(entries)``; so do a head mismatch and a record-count mismatch. Unanchored
    (``require_head=False``) the chain only proves internal consistency: dropping tail
    records, or rewriting the whole log from genesis, still verifies.
    """
    n_expected = None
    if isinstance(path_or_entries, (str, Path)):
        p = Path(path_or_entries)
        lines = [x for x in p.read_text().splitlines() if x.strip()]
        entries = [json.loads(x) for x in lines]
        if head is None and expected_head is None and (p.parent / "head.json").exists():
            head = p.parent / "head.json"
    else:
        entries = list(path_or_entries)
    if isinstance(head, (str, Path)):
        head = json.loads(Path(head).read_text())
    if expected_head is None and head is not None:
        expected_head, n_expected = head.get("chain_head"), head.get("n_records")
    prev = GENESIS
    for i, e in enumerate(entries):
        body = {k: v for k, v in e.items() if k != "entry_hash"}
        if e.get("prev_hash") != prev or e.get("verdict") not in VERDICTS:
            return False, i
        if e.get("verdict") == "dismiss" and not e.get("reason_code"):
            return False, i
        if hashlib.sha256(prev.encode() + canonical(body)).hexdigest() != e.get("entry_hash"):
            return False, i
        prev = e["entry_hash"]
    if expected_head is None:
        return (False, len(entries)) if require_head else (True, None)
    if prev != expected_head or (n_expected is not None and n_expected != len(entries)):
        return False, len(entries)
    return True, None
