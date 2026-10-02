"""Apply VERA migrations as the admin role, each file in ONE transaction.

    python db/apply_migrations.py 001 002          # apply
    python db/apply_migrations.py --dry-run 003    # run then ROLL BACK

Uses week-1v2/db.py get_admin_engine() (env from its .env.db-accounts).
Run with the week-1v2 venv. Credentials are never printed.
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent.parent / "AI-Internship" / "ai-engineering-bootcamp-v2" / "week-1v2"))
from db import get_admin_engine  # noqa: E402


def main(argv: list[str]) -> int:
    dry = "--dry-run" in argv
    prefixes = [a for a in argv if not a.startswith("--")]
    if not prefixes:
        print(__doc__)
        return 2
    engine = get_admin_engine()
    raw = engine.raw_connection()
    try:
        cur = raw.cursor()
        for p in prefixes:
            f = next(iter(sorted((HERE / "migrations").glob(f"{p}_vera_*.sql"))), None)
            if f is None:
                raise SystemExit(f"no migration matching {p}_vera_*.sql")
            cur.execute(f.read_text())
            print(f"{'DRY-RUN ok' if dry else 'applied'}: {f.name}")
        if dry:
            raw.rollback()
        else:
            raw.commit()
    except Exception as exc:
        raw.rollback()
        print(f"FAILED, rolled back: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    finally:
        raw.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
