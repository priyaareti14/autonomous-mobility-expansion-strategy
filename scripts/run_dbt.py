"""Run dbt with credentials loaded from the git-ignored .env.

dbt reads connection settings from dbt/profiles.yml, which only holds
env_var() references (template: dbt/profiles.example.yml). This wrapper
loads .env into the process environment and runs dbt in-process with the
project and profiles directory set to dbt/. No secret is printed.

Usage (repository root, .venv active):
    python scripts/run_dbt.py debug
    python scripts/run_dbt.py build
    python scripts/run_dbt.py docs generate
"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
DBT_DIR = ROOT / "dbt"


def main() -> int:
    load_dotenv(ROOT / ".env", override=False)
    profiles = DBT_DIR / "profiles.yml"
    if not profiles.exists():
        print("dbt/profiles.yml not found: copy dbt/profiles.example.yml to dbt/profiles.yml "
              "(it contains only env_var() references and is git-ignored).")
        return 2

    from dbt.cli.main import dbtRunner

    args = sys.argv[1:] or ["--help"]
    if args[0] != "--help":
        args += ["--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)]
    result = dbtRunner().invoke(args)
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
