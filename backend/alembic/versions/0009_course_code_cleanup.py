"""Normalize legacy course codes without changing course identities."""

import re

from alembic import op
import sqlalchemy as sa


revision = "0009_course_code_cleanup"
down_revision = "0008_course_materials"
branch_labels = None
depends_on = None

COURSE_CODE_RE = re.compile(r"^[A-Za-z]{4}[0-9]{4}$")


def upgrade():
    bind = op.get_bind()
    if "courses" not in set(sa.inspect(bind).get_table_names()):
        return

    rows = list(bind.execute(sa.text("SELECT id, code FROM courses ORDER BY id")))
    reserved = {str(row.code).strip().upper() for row in rows if row.code and COURSE_CODE_RE.fullmatch(str(row.code).strip())}
    used: set[str] = set(reserved)
    seen_valid: set[str] = set()
    changes: list[tuple[str, str, str]] = []
    next_number = 1
    for row in rows:
        raw = str(row.code or "").strip()
        normalized = raw.upper()
        if COURSE_CODE_RE.fullmatch(raw) and normalized not in seen_valid:
            seen_valid.add(normalized)
            changes.append((row.id, raw, normalized))
            continue
        while True:
            candidate = f"COUR{next_number:04d}"
            next_number += 1
            if candidate not in used:
                break
        used.add(candidate)
        changes.append((row.id, raw, candidate))

    temporary_used = {str(row.code or "") for row in rows}
    temporary_number = 1
    for row_id, raw, desired in changes:
        if raw == desired:
            continue
        while True:
            temporary = f"TMP{temporary_number:08d}"
            temporary_number += 1
            if temporary not in temporary_used:
                break
        temporary_used.add(temporary)
        bind.execute(sa.text("UPDATE courses SET code = :code WHERE id = :id"), {"code": temporary, "id": row_id})

    for row_id, raw, desired in changes:
        if raw != desired:
            bind.execute(sa.text("UPDATE courses SET code = :code WHERE id = :id"), {"code": desired, "id": row_id})


def downgrade():
    # Course identities and their relationships are intentionally preserved;
    # the old values are not recoverable from this migration.
    pass
