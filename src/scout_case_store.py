"""Local investigation records for Scout.

Why SQLite? This is a one-person course prototype. Python already includes it,
and a local database lets a case survive a browser refresh or app restart.
The file belongs on the user's computer, not in GitHub.
"""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

DEFAULT_DB = Path(__file__).resolve().parents[1] / "data" / "scout_cases.db"
NOTE_KINDS = {"confirmed_fact", "observation", "hypothesis", "verified_resolution"}
CASE_STATUSES = {"open", "resolved"}
MESSAGE_ROLES = {"user", "assistant"}
REVIEW_TARGETS = {"initial_reply", "ai_interpretation"}
REVIEW_OUTCOMES = {"supported", "not_supported", "uncertain"}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@contextmanager
def connect(db_path: str | Path = DEFAULT_DB):
    """One short-lived connection per action; commit, roll back and close.

    A context manager lets me write with connect(...) as db. It commits
    on success, rolls back on failure and closes the connection afterwards.
    """
    # Tests and isolated demos can select a disposable database without
    # changing normal production paths or function signatures.
    override = os.environ.get("SCOUT_CASE_DB")
    path = Path(override) if override and Path(db_path) == DEFAULT_DB else Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(path), timeout=10)
    connection.row_factory = sqlite3.Row
    # Foreign keys link messages and reviews to their parent case.
    # SQLite needs this switched on for each connection.
    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("PRAGMA busy_timeout = 10000")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialise_database(db_path: str | Path = DEFAULT_DB) -> None:
    """Create tables only if needed. Existing cases and messages are preserved."""
    with connect(db_path) as db:
        db.executescript(
            """
            CREATE TABLE IF NOT EXISTS scout_cases (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'open'
                    CHECK(status IN ('open','resolved')),
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scout_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL REFERENCES scout_cases(id) ON DELETE CASCADE,
                role TEXT NOT NULL CHECK(role IN ('user','assistant')),
                content TEXT NOT NULL,
                evidence_json TEXT NOT NULL DEFAULT '{}',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scout_notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL REFERENCES scout_cases(id) ON DELETE CASCADE,
                kind TEXT NOT NULL CHECK(kind IN (
                    'confirmed_fact', 'observation', 'hypothesis',
                    'verified_resolution'
                )),
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scout_verification_reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id TEXT NOT NULL REFERENCES scout_cases(id) ON DELETE CASCADE,
                message_id INTEGER NOT NULL REFERENCES scout_messages(id) ON DELETE CASCADE,
                target TEXT NOT NULL CHECK(target IN ('initial_reply','ai_interpretation')),
                outcome TEXT NOT NULL CHECK(outcome IN ('supported','not_supported','uncertain')),
                detail TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS scout_reviews_case_message
                ON scout_verification_reviews(case_id, message_id, id);
            CREATE INDEX IF NOT EXISTS scout_messages_case
                ON scout_messages(case_id, id);
            CREATE INDEX IF NOT EXISTS scout_notes_case
                ON scout_notes(case_id, id);
            CREATE INDEX IF NOT EXISTS scout_cases_updated
                ON scout_cases(updated_at);
            """
        )


def create_case(title: str, db_path: str | Path = DEFAULT_DB) -> dict:
    """Start an investigation. We never copy another case's chat into it."""
    title = title.strip()[:110] or "New investigation"
    case_id = str(uuid.uuid4())
    now = utc_now()
    with connect(db_path) as db:
        db.execute(
            "INSERT INTO scout_cases(id, title, status, created_at, updated_at) "
            "VALUES (?, ?, 'open', ?, ?)",
            (case_id, title, now, now),
        )
    return get_case(case_id, db_path)


def title_case_from_first_message(
    case_id: str, first_message: str,
    db_path: str | Path = DEFAULT_DB,
) -> None:
    """Name an untouched new case when its first incident description arrives.

    We only change the default title before any chat messages are saved.
    Existing, named cases keep their original name and history.
    """
    title = first_message.strip()[:110]
    if not title:
        return
    with connect(db_path) as db:
        _require_open_case(db, case_id)
        count = db.execute(
            "SELECT COUNT(*) FROM scout_messages WHERE case_id = ?",
            (case_id,),
        ).fetchone()[0]
        if count == 0:
            db.execute(
                "UPDATE scout_cases SET title = ?, updated_at = ? "
                "WHERE id = ? AND title = ?",
                (title, utc_now(), case_id, "New investigation"),
            )


def get_case(case_id: str, db_path: str | Path = DEFAULT_DB) -> dict | None:
    with connect(db_path) as db:
        row = db.execute(
            "SELECT id, title, status, created_at, updated_at "
            "FROM scout_cases WHERE id = ?", (case_id,),
        ).fetchone()
    return dict(row) if row else None


def list_cases(db_path: str | Path = DEFAULT_DB, limit: int = 100) -> list[dict]:
    with connect(db_path) as db:
        rows = db.execute(
            "SELECT id, title, status, created_at, updated_at "
            "FROM scout_cases ORDER BY updated_at DESC, rowid DESC LIMIT ?",
            (max(1, min(int(limit), 500)),),
        ).fetchall()
    return [dict(row) for row in rows]


def _require_open_case(db: sqlite3.Connection, case_id: str) -> None:
    row = db.execute("SELECT status FROM scout_cases WHERE id = ?", (case_id,)).fetchone()
    if row is None:
        raise ValueError("That investigation could not be found.")
    if row["status"] != "open":
        raise ValueError("This case is marked resolved. Reopen it before adding more details.")


def add_message(
    case_id: str, role: str, content: str,
    evidence: dict[str, Any] | None = None,
    db_path: str | Path = DEFAULT_DB,
) -> int:
    """Keep both sides of the exchange and source IDs for later review."""
    if role not in MESSAGE_ROLES:
        raise ValueError("Role must be user or assistant.")
    content = content.strip()
    if not content:
        raise ValueError("Cannot save an empty message.")
    now = utc_now()
    with connect(db_path) as db:
        _require_open_case(db, case_id)
        cursor = db.execute(
            "INSERT INTO scout_messages(case_id, role, content, evidence_json, created_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (case_id, role, content, json.dumps(evidence or {}), now),
        )
        db.execute(
            "UPDATE scout_cases SET updated_at = ? WHERE id = ?", (now, case_id),
        )
        return int(cursor.lastrowid)



def update_assistant_evidence(
    case_id: str, message_id: int, changes: dict[str, Any],
    db_path: str | Path = DEFAULT_DB,
) -> None:
    """Attach an optional LLM draft to an existing checked, saved reply.

    The original user-facing answer and its evidence cards remain unchanged.
    Updates are merged into evidence_json so an interrupted model request
    cannot destroy the initial investigation response.
    """
    if not isinstance(changes, dict) or not changes:
        raise ValueError("Evidence updates must be a non-empty dictionary.")
    allowed = {
        "model_draft", "model_draft_cited_ids", "model",
        "seconds", "tokens",
    }
    if set(changes) - allowed:
        raise ValueError("Only model-generation metadata can be updated.")
    now = utc_now()
    with connect(db_path) as db:
        _require_open_case(db, case_id)
        row = db.execute(
            "SELECT evidence_json FROM scout_messages "
            "WHERE id = ? AND case_id = ? AND role = 'assistant'",
            (message_id, case_id),
        ).fetchone()
        if row is None:
            raise ValueError("The assistant reply could not be found in this case.")
        evidence = json.loads(row["evidence_json"])
        evidence.update(changes)
        db.execute(
            "UPDATE scout_messages SET evidence_json = ? WHERE id = ? AND case_id = ?",
            (json.dumps(evidence), message_id, case_id),
        )
        db.execute(
            "UPDATE scout_cases SET updated_at = ? WHERE id = ?",
            (now, case_id),
        )


def add_verification_review(
    case_id: str, message_id: int, target: str, outcome: str,
    detail: str, db_path: str | Path = DEFAULT_DB,
) -> int:
    """Append a human-entered judgement about one specific saved reply or AI draft.

    AI code cannot call this through model metadata updates. The text of the
    original answer is never changed and previous review decisions are retained.
    """
    if target not in REVIEW_TARGETS:
        raise ValueError("Unknown item to review.")
    if outcome not in REVIEW_OUTCOMES:
        raise ValueError("Unknown review outcome.")
    detail = detail.strip()
    if len(detail) < 12:
        raise ValueError("Describe what you checked and what you found (12+ characters).")
    now = utc_now()
    with connect(db_path) as db:
        _require_open_case(db, case_id)
        row = db.execute(
            "SELECT evidence_json FROM scout_messages "
            "WHERE id = ? AND case_id = ? AND role = 'assistant'",
            (message_id, case_id),
        ).fetchone()
        if row is None:
            raise ValueError("The reply to review was not found in this case.")
        if target == "ai_interpretation":
            evidence = json.loads(row["evidence_json"])
            if not str(evidence.get("model_draft", "")).strip():
                raise ValueError("This reply has no AI interpretation to review.")
        cursor = db.execute(
            "INSERT INTO scout_verification_reviews"
            "(case_id, message_id, target, outcome, detail, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (case_id, message_id, target, outcome, detail, now),
        )
        db.execute(
            "UPDATE scout_cases SET updated_at = ? WHERE id = ?",
            (now, case_id),
        )
        return int(cursor.lastrowid)


def get_verification_reviews(
    case_id: str, db_path: str | Path = DEFAULT_DB,
) -> list[dict]:
    """Full append-only history; the UI uses the newest decision per target."""
    with connect(db_path) as db:
        rows = db.execute(
            "SELECT id, case_id, message_id, target, outcome, detail, created_at "
            "FROM scout_verification_reviews WHERE case_id = ? ORDER BY id",
            (case_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_messages(
    case_id: str, db_path: str | Path = DEFAULT_DB, limit: int | None = None,
) -> list[dict]:
    """Return messages oldest-first, including stored source references."""
    with connect(db_path) as db:
        if limit is None:
            rows = db.execute(
                "SELECT * FROM scout_messages WHERE case_id = ? ORDER BY id",
                (case_id,),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM (SELECT * FROM scout_messages WHERE case_id = ? "
                "ORDER BY id DESC LIMIT ?) ORDER BY id",
                (case_id, max(1, min(int(limit), 200))),
            ).fetchall()
    messages = []
    for row in rows:
        item = dict(row)
        item["evidence"] = json.loads(item.pop("evidence_json"))
        messages.append(item)
    return messages


def add_note(
    case_id: str, kind: str, content: str,
    db_path: str | Path = DEFAULT_DB,
) -> int:
    """A person chooses the evidence label; Scout never approves its own guesses."""
    if kind not in NOTE_KINDS:
        raise ValueError("Unknown note type.")
    content = content.strip()
    if not content:
        raise ValueError("Enter a note before saving it.")
    now = utc_now()
    with connect(db_path) as db:
        _require_open_case(db, case_id)
        cursor = db.execute(
            "INSERT INTO scout_notes(case_id, kind, content, created_at) "
            "VALUES (?, ?, ?, ?)", (case_id, kind, content, now),
        )
        db.execute(
            "UPDATE scout_cases SET updated_at = ? WHERE id = ?", (now, case_id),
        )
        return int(cursor.lastrowid)


def get_notes(case_id: str, db_path: str | Path = DEFAULT_DB) -> list[dict]:
    with connect(db_path) as db:
        rows = db.execute(
            "SELECT id, case_id, kind, content, created_at "
            "FROM scout_notes WHERE case_id = ? ORDER BY id",
            (case_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def set_case_status(
    case_id: str, status: str, db_path: str | Path = DEFAULT_DB,
) -> None:
    """Require an explicitly recorded verified outcome before marking resolved."""
    if status not in CASE_STATUSES:
        raise ValueError("Unknown case status.")
    with connect(db_path) as db:
        existing = db.execute(
            "SELECT status FROM scout_cases WHERE id = ?", (case_id,),
        ).fetchone()
        if existing is None:
            raise ValueError("That investigation could not be found.")
        if status == "resolved":
            verified_count = db.execute(
                "SELECT COUNT(*) FROM scout_notes WHERE case_id = ? "
                "AND kind = 'verified_resolution'", (case_id,),
            ).fetchone()[0]
            if not verified_count:
                raise ValueError(
                    "Record a human-verified resolution before closing this case."
                )
        db.execute(
            "UPDATE scout_cases SET status = ?, updated_at = ? WHERE id = ?",
            (status, utc_now(), case_id),
        )


def export_case(case_id: str, db_path: str | Path = DEFAULT_DB) -> dict:
    """A local JSON export the user controls; no data is uploaded anywhere."""
    record = get_case(case_id, db_path)
    if record is None:
        raise ValueError("That investigation could not be found.")
    return {
        "case": record,
        "notes": get_notes(case_id, db_path),
        "verification_reviews": get_verification_reviews(case_id, db_path),
        "conversation": get_messages(case_id, db_path),
    }


def delete_case(case_id: str, db_path: str | Path = DEFAULT_DB) -> None:
    """Delete this local record and its related notes/messages (foreign keys on)."""
    with connect(db_path) as db:
        db.execute("DELETE FROM scout_cases WHERE id = ?", (case_id,))
