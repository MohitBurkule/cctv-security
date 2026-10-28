"""H60: alarm cards, the sim-only GT guard, and the hash-chained evidence log."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from cctvsec.eval import alarm_card as ac
from cctvsec.eval import evidence_pack as ep
from cctvsec.eval.alarms import Alarm, TruthEvent, score


@pytest.fixture(scope="module")
def run_dir(tmp_path_factory) -> Path:
    out = tmp_path_factory.mktemp("h60") / "run"
    subprocess.run([sys.executable, "-m", "survsim.cli", "run",
                    "configs/scenarios/smoke_mock.yaml", "--out", str(out)],
                   check=True, capture_output=True)
    return out


def _alarms(run_dir):
    from cctvsec.eval.rules import run_baseline
    return sorted(run_baseline(run_dir, threshold_s=25.0), key=lambda a: a.t)


def test_real_mode_leak_count_is_zero(run_dir):
    alarms = _alarms(run_dir)
    assert alarms and all(a.uid for a in alarms)  # GT-rule alarms carry GT uids
    cards = ac.build_cards(run_dir, alarms, mode="real",
                           runner={0: ac.RunnerFields(score=0.97, theta=0.95, rank_in_queue=1)})
    assert len(cards) == len(alarms)
    gt_vals = ac.gt_values(run_dir)
    assert ac.leak_count(cards, gt_vals) == 0
    for c in cards:
        s = json.dumps(c)
        for k in ac.SIM_ONLY_KEYS:
            assert f'"{k}"' not in s
        for v in gt_vals:
            assert f'"{v}"' not in s
    assert cards[0]["score"] == 0.97 and cards[0]["rank_in_queue"] == 1


def test_sim_cards_would_leak_and_carry_gt(run_dir):
    alarms = _alarms(run_dir)
    cards = ac.build_cards(run_dir, alarms, mode="sim")
    assert ac.leak_count(cards, ac.gt_values(run_dir)) == len(cards)  # the guard detects it
    for c in cards:
        assert c["zone_id"] and len(c["box_xywh"]) == 4 and 0 <= c["visibility"] <= 1
        assert c["camera_health"] == "ok" and c["calib_ref"].startswith("calib/")
        assert c["gt_match"]["verdict"] in {"hit", "repeat", "late", "wrong_actor", "false"}


def test_alarm_ids_identical_across_modes_and_reruns(run_dir):
    a = _alarms(run_dir)
    ids = [c["alarm_id"] for c in ac.build_cards(run_dir, a, mode="sim")]
    assert ids == [c["alarm_id"] for c in ac.build_cards(run_dir, a, mode="real")]
    assert len(set(ids)) == len(ids)


def test_schema_rejects_sim_key_in_real_card():
    with pytest.raises(ValueError):
        ac.validate_card({"mode": "real", "alarm_id": "x", "t": 1.0, "gt_match": {}})
    with pytest.raises(ValueError):
        ac.validate_card({"mode": "real", "camera_pose": {"yaw": 0, "tamper": "spray"}})


def test_gt_match_hits_agree_with_score():
    truth = [TruthEvent(0, 60, "loiter", ("a",)), TruthEvent(100, 160, "loiter", ("b",))]
    alarms = [Alarm(5, "loiter", uid="a"), Alarm(7, "loiter", uid="a"),
              Alarm(104, "loiter", uid="c"), Alarm(130, "loiter", uid="b"), Alarm(300, "loiter")]
    m = ac.gt_matches(alarms, truth, tolerance_s=10)
    assert [m[i]["verdict"] for i in range(5)] == ["hit", "repeat", "wrong_actor", "late", "false"]
    s = score(truth, alarms, camera_hours=1, tolerance_s=10)
    hits = sorted(v["i_lids_delay_s"] for v in m.values() if v["verdict"] == "hit")
    assert hits == sorted(s.latencies_s)


def _cards():
    return [{"alarm_id": f"a{i}", "t": float(i)} for i in range(5)]


def test_chain_verifies_and_is_deterministic():
    dec = [("dispatch", None, 1.0), ("dismiss", "no_threat", 2.0), ("escalate", None, 3.0),
           ("bulk_ack", None, 4.0), ("dispatch", None, 5.0)]
    e1 = ep.chain(_cards(), dec, "alice", "s")
    e2 = ep.chain(_cards(), dec, "alice", "s")
    assert e1[-1]["entry_hash"] == e2[-1]["entry_hash"]
    assert ep.verify(e1, require_head=False) == (True, None)
    assert ep.verify(e1) == (False, 5)  # no head => fail closed
    assert all("alice" not in json.dumps(e) for e in e1)


@pytest.mark.parametrize("idx", range(5))
def test_verifier_catches_any_edit(idx, tmp_path):
    dec = [("dispatch", None, 1.0)] * 5
    entries = ep.chain(_cards(), dec, "alice", "s")
    p = tmp_path / "log.jsonl"
    ep.write_log(p, entries)
    lines = p.read_text().splitlines()
    rec = json.loads(lines[idx])
    rec["verdict"] = "dismiss"
    lines[idx] = json.dumps(rec, sort_keys=True)
    p.write_text("\n".join(lines) + "\n")
    assert ep.verify(p) == (False, idx)


def test_verifier_catches_deletion_and_bad_verdict():
    entries = ep.chain(_cards(), [("dispatch", None, 1.0)] * 5, "alice", "s")
    assert ep.verify(entries[:2] + entries[3:]) == (False, 2)
    with pytest.raises(ValueError):
        ep.make_entry(ep.GENESIS, _cards()[0], "a", "s", "ignore", 1.0)
    with pytest.raises(ValueError):
        ep.make_entry(ep.GENESIS, _cards()[0], "a", "s", "dismiss", 1.0)  # no reason


def test_cli_real_mode(run_dir, tmp_path):
    from typer.testing import CliRunner

    from cctvsec.cli import app
    r = CliRunner().invoke(app, ["alarm-cards", str(run_dir), "--mode", "real",
                                 "--out", str(tmp_path), "--insecure-default-salt"])
    assert r.exit_code == 0, r.output
    summ = json.loads((tmp_path / "summary.json").read_text())
    assert summ["leak_count"] == 0 and summ["chain_ok"] and summ["n_cards"] == summ["n_alarms"]


# --- AUDIT_H60 regressions -------------------------------------------------------------

def _rehash(entries):
    prev, out = ep.GENESIS, []
    for e in entries:
        body = {k: v for k, v in e.items() if k != "entry_hash"}
        body["prev_hash"] = prev
        body["entry_hash"] = ep.hashlib.sha256(prev.encode() + ep._canon(body)).hexdigest()
        out.append(body)
        prev = body["entry_hash"]
    return out


def test_verifier_detects_tail_truncation_only_with_anchored_head():
    entries = ep.chain(_cards(), [("dispatch", None, 1.0)] * 5, "alice", "s")
    head = entries[-1]["entry_hash"]
    assert ep.verify(entries[:3], require_head=False) == (True, None)  # unanchored: truncation is invisible
    assert ep.verify(entries[:3], expected_head=head) == (False, 3)
    assert ep.verify(entries, expected_head=head) == (True, None)


def test_verifier_reorder_and_replaced_first_record():
    entries = ep.chain(_cards(), [("dispatch", None, 1.0)] * 5, "alice", "s")
    assert ep.verify([entries[1], entries[0]] + entries[2:]) == (False, 0)
    first = dict(entries[0], verdict="escalate")
    assert ep.verify([first] + entries[1:]) == (False, 0)
    # A full rewrite from genesis passes unanchored; the anchored head catches it.
    forged = _rehash([first] + entries[1:])
    assert ep.verify(forged, require_head=False) == (True, None)
    assert ep.verify(forged, expected_head=entries[-1]["entry_hash"])[0] is False


def test_verifier_rejects_rehashed_dismiss_without_reason():
    entries = ep.chain(_cards(), [("dismiss", "no_threat", 1.0)] * 5, "alice", "s")
    bad = _rehash(entries[:2] + [dict(entries[2], reason_code=None)] + entries[3:])
    assert ep.verify(bad) == (False, 2)


def test_gt_values_include_zone_names(run_dir):
    vals = ac.gt_values(run_dir)
    assert any(v.startswith("zone.") for v in vals)


# --- H60 slice 2 ------------------------------------------------------------------------

def test_cli_real_mode_refuses_public_salt_and_uses_salt_file(run_dir, tmp_path):
    from typer.testing import CliRunner

    from cctvsec.cli import app
    r = CliRunner().invoke(app, ["alarm-cards", str(run_dir), "--mode", "real", "--out", str(tmp_path / "a")])
    assert r.exit_code == 2 and not (tmp_path / "a" / "cards.jsonl").exists()
    salt = tmp_path / "site.salt"
    args = ["alarm-cards", str(run_dir), "--mode", "real", "--salt-file", str(salt)]
    r = CliRunner().invoke(app, args + ["--init-salt", "--out", str(tmp_path / "b")])
    assert r.exit_code == 0, r.output
    assert len(salt.read_bytes()) == 32 and (salt.stat().st_mode & 0o777) == 0o600
    assert CliRunner().invoke(app, args + ["--init-salt", "--out", str(tmp_path / "c")]).exit_code != 0
    r = CliRunner().invoke(app, args + ["--out", str(tmp_path / "d")])
    assert r.exit_code == 0 and "ANCHOR THIS HEAD" in r.output
    log_b = (tmp_path / "b" / "evidence_log.jsonl").read_text()
    assert log_b == (tmp_path / "d" / "evidence_log.jsonl").read_text()  # same salt, same log
    pub = ep.hash_operator("operator-0", ep.DEFAULT_SALT)
    assert pub not in log_b
    assert json.loads((tmp_path / "b" / "summary.json").read_text())["salt"] == "file"
    assert "*.salt" in Path(".gitignore").read_text().split()


def test_head_json_makes_truncation_and_rechain_fail_closed(tmp_path):
    entries = ep.chain(_cards(), [("dispatch", None, 1.0)] * 5, "alice", "s")
    head = ep.write_pack(tmp_path, entries, created_at=0.0)
    log = tmp_path / "evidence_log.jsonl"
    assert head["n_records"] == 5 and json.loads((tmp_path / "head.json").read_text()) == head
    assert ep.verify(log) == (True, None)
    ep.write_log(log, entries[:3])                        # truncate from the end
    assert ep.verify(log) == (False, 3)
    forged = _rehash([dict(entries[0], verdict="escalate")] + entries[1:])
    ep.write_log(log, forged)                             # re-chain from genesis, same length
    assert ep.verify(log)[0] is False
    (tmp_path / "head.json").unlink()                     # no head at all
    ep.write_log(log, entries)
    assert ep.verify(log) == (False, 5)
    assert ep.verify(log, require_head=False) == (True, None)
    # a head with the right hash but a wrong record count also fails
    assert ep.verify(entries, head={"chain_head": head["chain_head"], "n_records": 4})[0] is False


def test_canonical_is_order_independent_and_jcs_numbers():
    a = {"b": 1, "a": [1.5, {"z": None, "y": True}], "é": "x\n", "c": -0.0}
    b = {"é": "x\n", "c": -0.0, "a": [1.5, {"y": True, "z": None}], "b": 1}
    assert ep.canonical(a) == ep.canonical(b)
    assert ep.canonical(a) == '{"a":[1.5,{"y":true,"z":null}],"b":1,"c":0,"é":"x\\n"}'.encode()
    # RFC 8785 appendix B / ECMAScript Number::toString vectors
    vec = {1.0: "1", 100.0: "100", 1e21: "1e+21", 1e20: "100000000000000000000", 1e-7: "1e-7",
           0.000001: "0.000001", 333333333.3333333: "333333333.3333333", -1.5e-9: "-1.5e-9",
           5e-324: "5e-324", 1.7976931348623157e308: "1.7976931348623157e+308", 0.1: "0.1",
           9007199254740992.0: "9007199254740992", 123.456: "123.456"}
    for x, want in vec.items():
        assert ep.canonical(x) == want.encode(), x
    assert ep.canonical(10 ** 20) == b"100000000000000000000"
    # UTF-16 code-unit key order (U+10000 sorts before U+FFFF-ish BMP chars above surrogates)
    assert ep.canonical({"\ufb01": 1, "\U0001f600": 2}) == '{"\U0001f600":2,"\ufb01":1}'.encode()
    for bad in (float("nan"), float("inf"), {"x": float("-inf")}):
        with pytest.raises(ValueError):
            ep.canonical(bad)


def test_cards_carry_config_model_and_clip_hashes(run_dir, tmp_path):
    import hashlib
    import shutil
    alarms = _alarms(run_dir)
    ck = tmp_path / "model.ckpt"
    ck.write_bytes(b"weights")
    cfg = Path("configs/scenarios/smoke_mock.yaml")
    cards = ac.build_cards(run_dir, alarms, mode="real", config_path=cfg, model_path=ck)
    assert cards[0]["config_hash"] == hashlib.sha256(cfg.read_bytes()).hexdigest()
    assert cards[0]["model_hash"] == hashlib.sha256(b"weights").hexdigest()
    assert all(c["clip_hash"] == ac.CLIP_NOT_EMITTED for c in cards)
    assert "model_hash" not in ac.build_cards(run_dir, alarms, mode="real")[0]
    # frames present -> clip hash over the alarm window; editing an in-window frame changes it
    rd = tmp_path / "run"
    shutil.copytree(run_dir, rd)
    fps = json.loads((rd / "meta" / "scenario.resolved.json").read_text())["fps"]
    t = alarms[0].t
    d = rd / "frames" / "cam_01"
    d.mkdir(parents=True)
    for n in range(int((t - 20) * fps), int((t + 20) * fps)):
        (d / f"{n:04d}.png").write_bytes(f"frame{n}".encode())
    h1 = ac.build_cards(rd, alarms[:1], mode="real")[0]["clip_hash"]
    assert h1 != ac.CLIP_NOT_EMITTED
    (d / f"{int(t * fps) + 3:04d}.png").write_bytes(b"edited")
    assert ac.build_cards(rd, alarms[:1], mode="real")[0]["clip_hash"] != h1
    far = rd / "frames" / "cam_01" / f"{int((t + 19) * fps):04d}.png"
    before = ac.build_cards(rd, alarms[:1], mode="real")[0]["clip_hash"]
    far.write_bytes(b"out of window")
    assert ac.build_cards(rd, alarms[:1], mode="real")[0]["clip_hash"] == before


def test_h22_scored_trace_is_passive_and_cards_fill_score_theta_rank(run_dir, tmp_path):
    import numpy as np

    from cctvsec.experiments.operator_queue import simulate
    worlds = [{"mode": "recall", "camera_hours": 1.0, "n_truth": 2,
               "arms": {"A1": [[20.0, 0.9, 1], [21.0, 0.95, 0], [22.0, 0.2, -1], [23.0, 0.99, -1]]}}]
    op = {"cameras": 1, "review_s": 30.0, "review_cv": 0.3, "shift_h": 8, "fatigue_after_h": 8,
          "fatigue_review_x": 1.0, "miss": 0.1, "miss_fatigued": 0.1, "bulk_ack_queue": 100,
          "horizons_s": [30, 300]}
    for pol in ("fifo", "ranked"):
        tr: list[dict] = []
        assert simulate(worlds, "A1", pol, 3, op, trace=tr) == simulate(worlds, "A1", pol, 3, op)
        assert len(tr) == 4 and all(r["verdict"] in ep.VERDICTS for r in tr)
    # ranked: at t=23 the queue holds 0.95 and 0.2 (0.9 is being reviewed) -> 0.99 ranks first
    assert [r["rank_in_queue"] for r in tr] == [1, 1, 2, 1]
    tr2: list[dict] = []
    simulate(worlds, "A1", "fifo", 0, {**op, "bulk_ack_queue": 1}, trace=tr2)
    assert any(r["verdict"] == "bulk_ack" for r in tr2)
    assert not np.isnan([r["t_verdict"] for r in tr2]).any()
    # card them via the CLI (real mode, salt file): score/theta/rank filled from the file
    rows = [dict(r, theta=0.95, label="suspicious.loiter") for r in tr]
    f = tmp_path / "alarms_scored.jsonl"
    f.write_text("".join(json.dumps(r) + "\n" for r in rows))
    from typer.testing import CliRunner

    from cctvsec.cli import app
    salt = tmp_path / "s.salt"
    r = CliRunner().invoke(app, ["alarm-cards", str(run_dir), "--mode", "real", "--alarms", str(f),
                                 "--salt-file", str(salt), "--init-salt", "--out", str(tmp_path / "o")])
    assert r.exit_code == 0, r.output
    cards = [json.loads(x) for x in (tmp_path / "o" / "cards.jsonl").read_text().splitlines()]
    assert [c["score"] for c in cards] == [r["score"] for r in rows]
    assert [c["rank_in_queue"] for c in cards] == [r["rank_in_queue"] for r in rows]
    assert all(c["theta"] == 0.95 for c in cards)
    log = [json.loads(x) for x in (tmp_path / "o" / "evidence_log.jsonl").read_text().splitlines()]
    assert [e["verdict"] for e in log] == [r["verdict"] for r in rows]
    s = json.loads((tmp_path / "o" / "summary.json").read_text())
    assert s["leak_count"] == 0 and s["chain_ok"] and s["filled"]["score"] == 4


def test_leak_guard_substring_and_identities(run_dir):
    """AUDIT_87 §5.2: a GT uid inside a longer string leaks; identities.parquet cells count."""
    alarms = _alarms(run_dir)
    cards = ac.build_cards(run_dir, alarms, mode="real")
    gt = ac.gt_values(run_dir)
    assert ac.leak_count(cards, gt) == 0
    assert "intruder" in gt  # identities.parquet role column
    bad = dict(cards[0], calib_ref=f"calib/{alarms[0].uid}_cam.json")
    assert ac.leak_count([bad], gt) == 1
    assert ac.leak_count([dict(cards[0], label="suspect intruder")], gt) == 1
    assert ac.leak_count([dict(cards[0], label="loiter")], gt | {"loiter"}) == 0  # allowlisted
    assert ac.leak_count([dict(cards[0], gt_uid="x")], gt) == 1  # by-key check kept


def test_verify_cards_binds_every_card_to_the_log(run_dir, tmp_path):
    """AUDIT_87 §5.1: an edited card fails with its alarm_id."""
    cards = ac.build_cards(run_dir, _alarms(run_dir), mode="real")
    entries = ep.chain(cards, [("escalate", None, c["t"]) for c in cards], "op", "salt")
    assert ep.verify_cards(entries, cards) == (True, None)
    edited = [dict(c) for c in cards]
    edited[1]["score"] = 0.5
    assert ep.verify_cards(entries, edited) == (False, cards[1]["alarm_id"])
    assert ep.verify_cards(entries, cards[:-1]) == (False, cards[-1]["alarm_id"])
    p = tmp_path / "cards.jsonl"
    p.write_text("".join(json.dumps(c) + "\n" for c in edited))
    assert ep.verify_cards(entries, p)[0] is False
