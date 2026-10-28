"""H66 decoy-flooding simulator: fast invariants."""
import copy
from pathlib import Path

import yaml

from cctvsec.experiments import RUNNERS
from cctvsec.experiments import decoy_flooding as D

CFG = yaml.safe_load(Path("cctvsec/experiments/configs/h66_decoy_flooding.yaml").read_text())


def test_registered():
    assert RUNNERS["decoy_flooding"] == "decoy_flooding"


def test_worlds_paired_and_hard_negative_has_no_intrusion():
    a0, a16, hn = (D.make_world(3, k, CFG) for k in (0, 16, None))
    bg = lambda al: [a for a in al if not a[5] and not a[3]]
    assert bg(a0) == bg(a16)                     # same background: arms are paired
    assert sum(a[5] for a in a16) == 16 and not any(a[5] for a in a0)
    assert not any(a[3] for a in hn) and sum(a[5] for a in hn) == CFG["world"]["hn_incident_k"]


def test_bulk_ack_drops_intrusion_but_escalation_keeps_it():
    op = dict(CFG["operator"], miss=0.0, miss_fatigued=0.0)
    decoy = [(float(t), "inc", 0.9, False, False, True) for t in range(12)]
    al = sorted(decoy + [(1.5, "per", 0.5, True, False, False)])
    fifo = D.simulate(al, "fifo", [0], op, 180.0)
    esc = D.simulate(al, "escalate", [0], op, 180.0)
    assert esc["rec300"] == 1.0 and esc["n_esc"] == 1
    assert fifo["rec300"] == 0.0                 # queue > 10 -> bulk-ack clears the intrusion alarm
    op2 = dict(op, escalated_exempt_bulk_ack=False)
    assert D.simulate(al, "escalate", [0], op2, 180.0)["n_esc"] == 1


def test_badged_alarm_is_not_escalated():
    al = [(0.0, "inc", 0.9, False, False, True), (5.0, "per", 0.5, False, True, False)]
    assert D.simulate(al, "escalate", [0], CFG["operator"], 180.0)["n_esc"] == 0


def test_summarise_small():
    c = copy.deepcopy(CFG)
    c.update(n_boot=50, operator_seeds=[0, 1])
    ws = [D._world_job((i, c)) for i in range(30)]
    r = D.summarise(ws, c)
    assert set(r["decision"]) >= {"met"} and "k16" in r["fifo_drop"]
    assert r["recall"]["k0/lane/@300"] == r["recall"]["k16/lane/@300"]  # lane is k-independent by construction
