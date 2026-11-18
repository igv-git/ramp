"""Plain-text export of progress (contracts/export.md): deterministic JSONL, no bodies, then derived counts.

Test output, diffs, review text, answers and card questions stay in profile.db (kept out of git).
"""

import json
from dataclasses import dataclass
from pathlib import Path

from ramp.store.repos import Store

FILES = ("concepts", "attempts", "due_queue", "bridge_flags", "card_reviews")


class ExportError(Exception):
    pass


@dataclass(frozen=True)
class Counts:
    slices_completed: int
    cards_answered: int
    bridge_flags: int
    pending_reviews: int


def _line(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def _ratings(review_json: str | None) -> dict[str, int]:
    """Concept -> rating from a stored review; the lowest rating wins when a concept appears twice."""
    if not review_json:
        return {}
    out: dict[str, int] = {}
    for r in json.loads(review_json).get("concept_ratings", []):
        out[r["concept"]] = min(r["rating"], out.get(r["concept"], r["rating"]))
    return out


def _records(store: Store) -> dict[str, list[dict]]:
    cards = {c["card_id"]: c for c in store.all_cards()}
    teachbacks = {t["attempt_id"] for t in store.list_teachbacks()}
    concepts = [
        {"id": c["id"], "skill": c["skill"], "name": c["name"], "bridge_note": c["bridge_note"],
         "has_card": c["card_id"] is not None,
         "card_due": cards[c["card_id"]]["due"] if c["card_id"] in cards else None}
        for c in store.list_concepts()]
    attempts = [
        {"id": a["id"], "slice_id": a["slice_id"], "ts": a["ts"], "status": a["status"], "verdict": a["verdict"],
         "passed": None if a["passed"] is None else bool(a["passed"]), "hints_used": a["hints_used"],
         "fingerprint": a["fingerprint"], "fingerprint_changed": bool(a["fingerprint_changed"]),
         "blocked_cause": a["blocked_cause"], "has_teachback": a["id"] in teachbacks,
         "ratings": _ratings(a["review_json"])}
        for a in store.list_attempts()]
    due = [{"card_id": c["card_id"], "concept_id": c["concept_id"], "due": c["due"],
            "state": json.loads(c["card_json"]).get("state")}
           for c in sorted(cards.values(), key=lambda c: c["card_id"])]
    flags = [{"id": f["id"], "slice_id": f["slice_id"], "bridge_no": f["bridge_no"], "note": f["note"],
              "ts": f["ts"]} for f in store.list_bridge_flags()]
    reviews = [{"id": r["id"], "card_id": r["card_id"], "ts": r["ts"], "grade": r["grade"], "rating": r["rating"]}
               for r in store.list_card_reviews()]
    return {"concepts": concepts, "attempts": attempts, "due_queue": due, "bridge_flags": flags,
            "card_reviews": reviews}


def export_all(store: Store, home: Path) -> None:
    out = Path(home) / "exports"
    try:
        out.mkdir(exist_ok=True)
        for name, rows in _records(store).items():
            (out / f"{name}.jsonl").write_text("".join(_line(r) + "\n" for r in rows), encoding="utf-8")
    except OSError as e:
        raise ExportError(f"cannot write {out}: {e}") from None


def _read(home: Path, name: str) -> list[dict]:
    path = Path(home) / "exports" / f"{name}.jsonl"
    try:
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    except (OSError, ValueError) as e:
        raise ExportError(f"cannot read {path}: {e}") from None


def counts(home: Path) -> Counts:
    """Derived from the exported files only, so the report and the files cannot disagree."""
    attempts = _read(home, "attempts")
    return Counts(
        slices_completed=len({a["slice_id"] for a in attempts if a["passed"] and a["has_teachback"]}),
        cards_answered=len(_read(home, "card_reviews")),
        bridge_flags=len(_read(home, "bridge_flags")),
        pending_reviews=sum(1 for a in attempts if a["status"] == "pending_review"),
    )


def format_counts(c: Counts) -> str:
    return (f"slices completed: {c.slices_completed} · cards answered: {c.cards_answered} · "
            f"bridge flags: {c.bridge_flags} · pending reviews: {c.pending_reviews}")
