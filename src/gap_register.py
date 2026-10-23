"""Color C card 16 — gap register (the revision loop agreed with the instructor).

Status per AI system × requirement (requirements from data/requirements_checklist.json):
    open      evidence_incomplete / evidence_not_found, or never reviewed
    complete  an APPROVED internal_update found evidence_found (after the user uploaded a revision)
    re_check  was complete, then a new regulation was uploaded

Run:  python -m src.gap_register --system "Credit Decision Support AI"
"""
from __future__ import annotations

import argparse
import datetime as dt
import json

from src.config import DATA_DIR

REGISTER = DATA_DIR / "gap_register.json"
CHECKLIST = DATA_DIR / "requirements_checklist.json"
TO_STATUS = {"evidence_found": "complete", "evidence_incomplete": "open", "evidence_not_found": "open"}


def _load() -> dict:
    return json.loads(REGISTER.read_text(encoding="utf-8")) if REGISTER.exists() else {"systems": {}, "history": []}


def _save(reg: dict) -> None:
    DATA_DIR.mkdir(exist_ok=True)
    REGISTER.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")


def status_table(ai_system: str) -> list[dict]:
    items = _load()["systems"].get(ai_system, {})
    rows = []
    for req in json.loads(CHECKLIST.read_text(encoding="utf-8")):
        item = items.get(req["requirement_id"], {})
        rows.append({"requirement_id": req["requirement_id"], "requirement": req["name"],
                     "ai_act_reference": req["ai_act_reference"], "status": item.get("status", "open"),
                     "sources": ", ".join(item.get("sources", [])), "updated_at": item.get("updated_at", ""),
                     "approved_by": item.get("approved_by", "")})
    return rows


def all_complete(ai_system: str) -> bool:
    return all(r["status"] == "complete" for r in status_table(ai_system))


def validate_findings(findings: list[dict], supplied: dict[str, str]) -> list[str]:
    """Problems that block a register update. `supplied` maps label → full citation of the draft's context.

    - requirement_id must be in the checklist
    - status must be an evidence label
    - every source must be a label that was supplied to the draft
    - evidence_found needs at least one company document [P#] as support
    """
    known = {r["requirement_id"] for r in json.loads(CHECKLIST.read_text(encoding="utf-8"))}
    problems = []
    for f in findings:
        rid, status, sources = f.get("requirement_id"), f.get("status"), f.get("sources", [])
        if rid not in known:
            problems.append(f"{rid}: not a requirement in the checklist")
        if status not in TO_STATUS:
            problems.append(f"{rid}: unknown evidence status {status!r}")
        unknown = [s for s in sources if s not in supplied]
        if unknown:
            problems.append(f"{rid}: cites sources that were not supplied ({', '.join(map(str, unknown))})")
        if status == "evidence_found" and not any(s in supplied and s.startswith("P") for s in sources):
            problems.append(f"{rid}: evidence_found without a supporting company document [P#]")
    return problems


def record_approved(ai_system: str, findings: list[dict], reviewer: str,
                    supplied: dict[str, str] | None = None) -> list[str]:
    """Call ONLY after a human approved the draft. Returns the list of status changes.

    All findings are validated first; if any is invalid, nothing is written (ValueError).
    """
    supplied = supplied or {}
    problems = validate_findings(findings, supplied)
    if problems:
        raise ValueError("Gap register not updated: " + "; ".join(problems))
    reg = _load()
    items = reg["systems"].setdefault(ai_system, {})
    now = dt.datetime.now().isoformat(timespec="seconds")
    changes = []
    for f in findings:
        new = TO_STATUS[f["status"]]
        old = items.get(f["requirement_id"], {}).get("status", "open")
        items[f["requirement_id"]] = {"status": new, "finding": f["status"], "note": f.get("note", ""),
                                      "sources": [f"{s}: {supplied[s]}" for s in f.get("sources", [])],
                                      "updated_at": now, "approved_by": reviewer}
        if new != old:
            changes.append(f"{f['requirement_id']}: {old} → {new}")
    reg["history"].append({"at": now, "system": ai_system, "event": "approved", "by": reviewer, "changes": changes})
    _save(reg)
    return changes


def mark_recheck(reason: str) -> list[str]:
    """A new regulation was uploaded: complete items must be reviewed again."""
    reg = _load()
    now = dt.datetime.now().isoformat(timespec="seconds")
    changes = []
    for system, items in reg["systems"].items():
        for req_id, item in items.items():
            if item["status"] == "complete":
                item.update(status="re_check", updated_at=now)
                changes.append(f"{system} {req_id}: complete → re_check")
    reg["history"].append({"at": now, "event": "regulation_upload", "reason": reason, "changes": changes})
    _save(reg)
    return changes


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--system", default="Credit Decision Support AI")
    for row in status_table(p.parse_args().system):
        print(f"{row['requirement_id']:8} {row['status']:9} {row['requirement']}")
