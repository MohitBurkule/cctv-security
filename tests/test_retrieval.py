"""Tests for natural-language event retrieval.

Retrieval on real footage is usually demonstrated rather than measured, because
nobody knows the true answer. Here the truth is exact, so these tests check the
things that decide whether a search result can be trusted: that filters are
applied correctly, that appearance is matched *per epoch*, and that terms the
index cannot express are reported instead of silently ignored.
"""

from __future__ import annotations

import json

import pytest

from cctvsec.eval.retrieval import (
    IndexedEvent,
    build_index,
    evaluate_queries,
    parse,
    search,
)

ZONES = ("zone.gate_b", "zone.concourse", "zone.restricted")


def _index() -> list[IndexedEvent]:
    return [
        IndexedEvent("e1", "p1", "suspicious.loiter.pace", 100.0, 400.0,
                     zone="zone.gate_b", colour="#c81414", garments=("rain_jacket", "jeans")),
        IndexedEvent("e2", "p2", "normal.commute_wait", 120.0, 300.0,
                     zone="zone.gate_b", colour="#1414c8", garments=("coat",)),
        IndexedEvent("e3", "p3", "suspicious.loiter.scan", 900.0, 930.0,
                     zone="zone.concourse", colour="#c81414", garments=("hoodie",)),
        IndexedEvent("e4", "p4", "hostile.aggression.fight", 500.0, 520.0,
                     zone="zone.concourse", colour="#2b2b2b", garments=("tshirt",)),
        IndexedEvent("e5", "p5", "hostile.tamper.camera.spray", 700.0, 740.0,
                     zone="zone.restricted", colour="#f5e600", garments=("hi_vis_vest",)),
    ]


# -------------------------------------------------------------------- parse


def test_behaviour_terms_are_recognised() -> None:
    assert parse("show me loitering").behaviour == "loiter"
    assert parse("anyone fighting").behaviour == "fight"
    assert parse("someone who collapsed").behaviour == "person_down"


def test_colour_and_garment_are_extracted() -> None:
    q = parse("man in a red jacket")
    assert q.colour == "red"
    assert q.garment == "jacket"


def test_zone_is_matched_on_its_readable_name() -> None:
    assert parse("loitering near gate b", ZONES).zone == "zone.gate_b"


def test_clock_times_become_filters() -> None:
    assert parse("loitering after 22:00").after_s == 22 * 3600
    assert parse("anything before 6am").before_s == 6 * 3600
    assert parse("loitering after 10pm").after_s == 22 * 3600


def test_duration_constraints_are_parsed() -> None:
    assert parse("loitering for more than 2 minutes").min_duration_s == 120.0
    assert parse("waiting at least 30 seconds").min_duration_s == 30.0


def test_terms_the_index_cannot_express_are_reported_not_dropped() -> None:
    """'Looks nervous' is where a language model earns its place; say so."""
    q = parse("someone acting nervous and suspicious")
    assert "nervous" in q.unparsed
    assert q.behaviour is None


def test_parser_is_auditable() -> None:
    """An operator must be able to see what the words became."""
    parsed = parse("red jacket loitering near gate b after 22:00", ZONES).as_dict()
    assert parsed["colour"] == "red"
    assert parsed["behaviour"] == "loiter"
    assert parsed["zone"] == "zone.gate_b"
    assert parsed["after_s"] == 22 * 3600


# ------------------------------------------------------------------- search


def test_behaviour_filter_excludes_other_events() -> None:
    hits = [e.event_id for e, _ in search(parse("loitering"), _index())]
    assert set(hits) == {"e1", "e3"}


def test_combined_filters_narrow_correctly() -> None:
    """The query that motivates the whole feature."""
    hits = [e.event_id for e, _ in search(parse("red jacket loitering near gate b", ZONES),
                                          _index())]
    assert hits == ["e1"]


def test_colour_matching_tolerates_shades() -> None:
    """#c81414 is red without being pure red."""
    hits = [e.event_id for e, _ in search(parse("red"), _index())]
    assert "e1" in hits and "e3" in hits
    assert "e2" not in hits            # blue


def test_duration_filter_removes_brief_events() -> None:
    hits = [e.event_id for e, _ in search(parse("loitering for more than 2 minutes"),
                                          _index())]
    assert hits == ["e1"]              # e3 lasts 30 s


def test_longer_events_rank_above_brief_ones() -> None:
    """An operator asking about loitering wants the long dwell, not a blip."""
    ranked = [e.event_id for e, _ in search(parse("loitering"), _index())]
    assert ranked[0] == "e1"


def test_unmatched_query_returns_nothing_rather_than_guessing() -> None:
    assert search(parse("fighting near gate b", ZONES), _index()) == []


def test_ununderstood_query_returns_nothing_not_everything() -> None:
    """Returning the whole index would read as a confident answer to a question
    that was never understood — the exact failure this module claims to avoid."""
    q = parse("someone acting shifty")
    assert q.understood is False
    assert search(q, _index()) == []
    assert "shifty" in q.unparsed


def test_query_explains_itself_to_the_operator() -> None:
    q = parse("red jacket loitering near gate b after 22:00", ZONES)
    explanation = q.explain()
    assert "behaviour=loiter" in explanation and "colour=red" in explanation

    unknown = parse("someone behaving oddly")
    assert "nothing in this query maps" in unknown.explain()


# -------------------------------------------------------- appearance epochs


def test_appearance_is_joined_per_epoch_not_per_person() -> None:
    """Someone who changed jacket must match 'red' only while wearing it.

    Joining on the person instead would return the disguised second half too,
    which is precisely the mistake the appearance-epoch model exists to prevent.
    """
    events = [
        {"event_id": "before", "actors": ["p1"], "label": "suspicious.loiter",
         "t_start": 50.0, "t_end": 80.0, "zone": "zone.gate_b"},
        {"event_id": "after", "actors": ["p1"], "label": "suspicious.loiter",
         "t_start": 500.0, "t_end": 530.0, "zone": "zone.gate_b"},
    ]
    identities = [
        {"uid": "p1", "epoch": 0, "t_from": 0.0, "t_to": 300.0,
         "dominant_colour": "#c81414", "outfit": json.dumps({"outer": "rain_jacket"})},
        {"uid": "p1", "epoch": 1, "t_from": 300.0, "t_to": 900.0,
         "dominant_colour": "#1414c8", "outfit": json.dumps({"outer": "none",
                                                              "top": "tshirt"})},
    ]
    index = build_index(events, identities)
    hits = [e.event_id for e, _ in search(parse("red"), index)]

    assert hits == ["before"]
    assert [e.event_id for e, _ in search(parse("blue"), index)] == ["after"]


def test_index_survives_missing_identity_rows() -> None:
    index = build_index([{"event_id": "x", "actors": ["ghost"],
                          "label": "suspicious.loiter", "t_start": 0.0, "t_end": 10.0}], [])
    assert index[0].colour is None
    assert search(parse("loitering"), index)


# --------------------------------------------------------------- evaluation


def test_queries_are_scored_against_known_answers() -> None:
    """The point of doing this in a simulator: the true answer is known."""
    cases = [
        ("loitering near gate b", {"e1"}),
        ("fighting", {"e4"}),
        ("camera tampering", {"e5"}),
    ]
    result = evaluate_queries(cases, _index(), ZONES, k=5)

    assert result["recall@5"] == pytest.approx(1.0)
    assert result["mrr"] == pytest.approx(1.0)
    assert result["n_queries"] == 3


def test_evaluation_reports_unparsed_terms_per_query() -> None:
    result = evaluate_queries([("someone behaving oddly", set())], _index(), ZONES)
    assert result["per_query"][0]["unparsed_terms"]


def test_failed_query_scores_zero_rather_than_erroring() -> None:
    result = evaluate_queries([("loitering near gate b", {"nonexistent"})],
                              _index(), ZONES)
    assert result["recall@5"] == 0.0
    assert result["per_query"][0]["first_hit_rank"] is None
