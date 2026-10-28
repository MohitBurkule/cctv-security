# AUDIT_87 · Mock interview round 7 (security/assurance), from a hostile security lead

Audited 2026-09-27 against `70a4545` (87 as written), re-checked at `09a5e4f` (gap fixes by a
parallel agent, `a633a1d`). Code read: `survsim/eval/{alarm_card,evidence_pack}.py`,
`survsim/cli.py` `alarm-cards`, `survsim/core/loader.py`, `scripts/hooks/`, `pyproject.toml`.
`tests/test_alarm_card.py` 22 pass. Probes in scratchpad only; no GPU, editor or `out/`.
**Score: 8/10.** Every number traces to its source and the caveats about the anchor are honest.
But two claims said more than the code does: the leak guard's value list (Q5) and "detects
changes after the card is written" (Q7, and the same wording in 63). Both are fixed in the docs.

## 1. Technical claims vs code

| 87 claim | code / test | verdict |
|---|---|---|
| Q1 `entry_hash = sha256(prev_hash ‖ canonical(record))`, fixed genesis | `make_entry`: `sha256(prev.encode() + canonical(rec))`, where `rec` also contains `prev_hash`; `GENESIS = "0"*64` | [V] |
| Q1 5/5 edits caught at index, plus reorder | `test_verifier_catches_any_edit` (parametrised ×5), `test_verifier_reorder_and_replaced_first_record` | [V] |
| Q1 RFC 8785-compatible *for the subset*, not checked against an external JCS lib | `_jcs`: UTF-16 key order, ES number form, NaN/Inf refused; 13 vectors in test; no external lib | [V]. Probe: ints are emitted as-is, so `2**53+1` → `9007199254740993` where JCS/ES gives `…992`. This is outside the subset used (cards carry no such ints), so the "subset" qualifier is doing real work |
| Q2 `head.json` {chain_head, n_records, created_at}; verify fails closed without it, on head or count mismatch | `write_pack`, `verify`; `test_head_json_makes_truncation_and_rechain_fail_closed` | [V]. Minor: `verify(..., expected_head=)` skips the `n_records` check (probe: 3 entries plus the correct hash → `(True, None)`). Harmless, because the hash already fixes the length |
| Q2 CLI prints `ANCHOR THIS HEAD out of band` | `cli.py` l. 288; asserted in `test_cli_real_mode_refuses_public_salt_and_uses_salt_file` | [V] |
| Q3 no signature / RFC 3161 on head | not in code; listed in 32 §H60 slice 2 remaining gaps | [V] |
| Q4 salt: 32 bytes from `secrets`, 0600, refuses overwrite, `*.salt` ignored, real exits 2 without it unless `--insecure-default-salt`; public-salt hash absent | `cli.py` l. 213–234 (`O_EXCL`, `token_bytes(32)`, `>= 32` bytes enforced on read); `.gitignore` l. 18; test asserts all of this | [V]. Note: the salt used is `raw.hex()`, i.e. `sha256(hex|id)`. Not HMAC, as 87 itself says |
| Q5 key whitelist `REAL_KEYS`; GT uid dropped in real mode | `validate_card` on every card; `gt_uid` is set only under `sim is not None` | [V] |
| Q5 `leak_count` greps by value for "every GT uid, event id, zone name **and identities cell**" | `gt_values` = `track_ids.json` keys, events `event_id` + `actors`, `world.parquet` zones. **No `identities.parquet`**. Needles are whole quoted strings `"v"`, so a value inside a longer string is missed (probe: `{"label":"entered lobby_A"}` → leak 0) | **Overclaim → fixed in 87 Q5.** The identities check was AUDIT_H60's manual check (FACTS row), not the shipped guard. The substring gap is new |
| Q5 0/2 slice 1; 0 over 9 654 H22 rows | FACTS H60 row; 32 §H60 slice 2 | [V] |
| Q7 `alarm_id` hashes run, camera, t, track, label, index | `alarm_id()` | [V] |
| Q7 reason-less dismiss rejected by verify | `verify` l. "dismiss and not reason_code"; `test_verifier_rejects_rehashed_dismiss_without_reason` | [V] |
| Q7 "The pack detects changes *after* the card is written" | `verify` reads only `evidence_log.jsonl`; nothing recomputes `card_sha256` against `cards.jsonl` (grep: only `make_entry` uses it). Probe: edit a card in `cards.jsonl` → `verify` = `(True, None)` | **Overclaim → fixed in 87 Q7 and 63 B2.** Cards are bound to the log only if a reviewer recomputes the hash; there is no card-vs-log verifier (gap) |
| Q8 `model_hash` = sha256 of `--model`, absent without it; `config_hash` over `--config` else `scenario.resolved.json` | `build_cards` | [V] |
| Q10 bulk_ack 2 431 of 9 654 | 32 §H60 slice 2 (dispatch 210 / dismiss 7 013 / bulk_ack 2 431; these sum to 9 654) | [V] |
| Q12 "four [tests] in AUDIT_H60"; 7/10 | AUDIT_H60 §4 "Four regression tests (13 → 17)"; score 7/10 | [V] |
| Q14 backend client defaults to `127.0.0.1` | `survsim/backends/unreal/backend.py` l. 55 | [V] |

## 2. Gap statements (Q12–Q14), re-verified

| gap as written at `70a4545` | at `70a4545` | now (`a633a1d`) |
|---|---|---|
| no secret scanner in the hook | [V]: hook = ruff, compileall, check tests | fixed: `scripts/hooks/secret_scan.py` runs first in the hook, with a test |
| deps unpinned, no lock file | [V]: `pyproject.toml` has only `pydantic>=2` as a bound; no lock | partly fixed: `requirements-lock.txt` pins exact versions, **0 hashes** (87 Q13 now says so) |
| `!include` "resolves relative paths, which I'd confine" | **understated.** Reproduced with a throwaway `configs/scen/a.yaml` containing `!include ../../secret/s.yaml` → loaded `{'api_key': 'LEAKED-123'}` from outside the tree. `!include /etc/hostname` → loaded the host name, so absolute paths worked too, and non-YAML files were read as scalars | fixed: the same two files raise `IncludeError` ("outside the config root", "absolute paths are not allowed"); `tests/test_loader_include.py` |

The parallel fix commit (`09a5e4f`) had already reworded Q12–Q14. This audit adds a gap-status note
to 87's header.

## 3. Red-flag scan and the new registry row

`tamper-proof` / `compliant` across `docs/**/*.md` and `CLAUDE.md` (50 hits). Almost all are
negations, red-flag lists, quotes, or third-party categories (NDAA, ONVIF, ITAR, BS 8418). Three were
not:

* `12` "### batch_v7: the compliant set" → "the licence-compliant (CC0) set".
* `47` "## 3. Recommended compliant character stack" → "licence-compliant" (no inbound anchors).
* `D04` a URL slug (`…/compliant-data-protection-…`); exempted by the row as a URL.

"Secure" used affirmatively in 87/46/63/86: none. "E · Secure development" is the name of the
practice, not a claim. **R58** added to `RETIRED_CLAIMS.md`: it flags `tamper-proof` and bare
`compliant` unless the line negates it, is a red flag, is quoted, is licence-qualified, is a
third-party category or is a URL. The row's exempt column is documentation only: `is_exempt` never
reads it, so the exemptions live in the pattern's lookahead, as in R52/R55. Both doc tests pass.

## 4. 63 threat model and 46 story 25

* 63 Part B2 paragraph matches the code except "from the moment a card is written: in-record
  edits". Reworded to cover the log, and the missing `cards.jsonl` binding was added to the
  not-covered list.
* Story 25: 7/10, 13 → 17 → 22 tests, leak 0 of 9 654 all match AUDIT_H60 and 32. "For each defect I
  wrote the failing test first" cannot be checked from AUDIT_H60, which records fixes and their
  tests but not their order. The salt defect had no test in slice 1 (it was doc-only; the salt test
  came in slice 2). Left as is: this is framing, not a number.

## 5. Open (not fixed here; code is out of scope)

1. ~~No card-vs-log verifier~~ — **closed in e3f7e13**: `evidence_pack.verify_cards`.
2. ~~`leak_count` whole strings only; `gt_values` omits `identities.parquet`~~ — **closed in
   e3f7e13** (substring match + identities strings). The whitelist remains the real control.
3. `expected_head=` path ignores `n_records` (cosmetic).
4. The lock file has no hashes. There is no SBOM.
