"""Phase 2 validation: Python -> Snowflake connectivity and warehouse foundation.

Checks, in order:
  1. Key-pair connection succeeds; session context (account, region, user,
     role, warehouse, database, version).
  2. Expected objects exist: database, six schemas, warehouse configuration,
     four project roles; project table counts per schema are reported.
  3. Least privilege: the service user holds the three functional roles and
     not AM_ADMIN.
  4. Privilege tests per role, using empty, temporary ZZ_PHASE2_* check
     objects. Every check object is dropped at the end, even after a failure.
     No project data is read or written.

Usage (from the repository root, with .venv active):
    python scripts/validate_snowflake_connection.py [--show-identifiers]

Exits with status 0 only if every check passes.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from snowflake.connector.errors import ProgrammingError  # noqa: E402

from src.utils.snowflake_connection import (  # noqa: E402
    SnowflakeConfigError,
    get_connection,
    load_config,
)

DB = "AUTONOMOUS_MOBILITY"
WH = "AM_EXPANSION_WH"
SCHEMAS = ("RAW", "STAGING", "INTERMEDIATE", "CORE", "ANALYTICS", "META")
PROJECT_ROLES = ("AM_ADMIN", "AM_INGESTOR", "AM_TRANSFORMER", "AM_ANALYST")
FUNCTIONAL_ROLES = ("AM_INGESTOR", "AM_TRANSFORMER", "AM_ANALYST")
CHECK = "ZZ_PHASE2_PRIV_CHECK"   # temporary, empty, always dropped

# Snowflake error numbers for privilege denials:
#   3001 = insufficient privileges
#   2003 = object does not exist or not authorized
#   3509 = not authorized in a managed access schema (grant by a non-owner)
DENIED_ERRNOS = {3001, 2003, 3509}


@dataclass
class Result:
    name: str
    passed: bool
    detail: str = ""


results: list[Result] = []


def record(name: str, passed: bool, detail: str = "") -> None:
    results.append(Result(name, passed, detail))
    mark = "PASS" if passed else "FAIL"
    print(f"  [{mark}] {name}" + (f" | {detail}" if detail else ""))


def mask(value: str, show: bool) -> str:
    if show or not value:
        return value
    return value[:2] + "*" * max(len(value) - 4, 3) + value[-2:]


def run(cur, sql: str):
    cur.execute(sql)
    return cur.fetchall()


def use_role(cur, role: str) -> None:
    cur.execute(f"USE ROLE {role}")
    # Only the primary role may authorize statements during the tests.
    cur.execute("USE SECONDARY ROLES NONE")


def expect(cur, role: str, sql: str, should_succeed: bool, label: str) -> None:
    use_role(cur, role)
    try:
        cur.execute(sql)
        cur.fetchall()
        outcome, detail = True, "succeeded"
    except ProgrammingError as exc:
        if exc.errno not in DENIED_ERRNOS:
            record(f"{role}: {label}", False, f"unexpected error {exc.errno}: {exc.msg}")
            return
        outcome, detail = False, f"denied (errno {exc.errno})"
    passed = outcome == should_succeed
    expected = "allowed" if should_succeed else "denied"
    record(f"{role}: {label}", passed, f"expected {expected}, {detail}")


def cleanup(cur) -> None:
    """Drop every check object through its owning role. Never raises."""
    drops = [
        ("AM_INGESTOR", f"DROP TABLE IF EXISTS {DB}.RAW.{CHECK}"),
        ("AM_INGESTOR", f"DROP TABLE IF EXISTS {DB}.META.{CHECK}"),
    ] + [
        ("AM_TRANSFORMER", f"DROP TABLE IF EXISTS {DB}.{s}.{CHECK}")
        for s in ("STAGING", "INTERMEDIATE", "CORE", "ANALYTICS")
    ] + [
        ("AM_TRANSFORMER", f"DROP VIEW IF EXISTS {DB}.ANALYTICS.{CHECK}_V"),
        # Only exist if a "should be denied" test wrongly succeeded:
        ("AM_TRANSFORMER", f"DROP TABLE IF EXISTS {DB}.RAW.{CHECK}_X"),
        ("AM_ANALYST", f"DROP TABLE IF EXISTS {DB}.ANALYTICS.{CHECK}_Y"),
    ] + [
        ("AM_INGESTOR", f"DROP TABLE IF EXISTS {DB}.{s}.{CHECK}")
        for s in ("STAGING", "INTERMEDIATE", "CORE", "ANALYTICS")
    ]
    for role, sql in drops:
        try:
            use_role(cur, role)
            cur.execute(sql)
        except ProgrammingError as exc:
            # A denial means this role could not have created the object;
            # the leftover check after cleanup is the authoritative test.
            if exc.errno not in DENIED_ERRNOS:
                print(f"  [WARN] cleanup failed ({role}): {exc.errno}")


def check_context(cur, show_ids: bool) -> None:
    print("\n1. Connection and session context")
    row = run(cur, """
        SELECT CURRENT_ACCOUNT(), CURRENT_REGION(), CURRENT_USER(), CURRENT_ROLE(),
               CURRENT_WAREHOUSE(), CURRENT_DATABASE(), CURRENT_VERSION()
    """)[0]
    labels = ("account", "region", "user", "role", "warehouse", "database", "version")
    values = dict(zip(labels, row))
    for key in ("account", "user"):
        values[key] = mask(values[key] or "", show_ids)
    for key, val in values.items():
        print(f"     {key:<10} {val}")
    record("key-pair connection established", True)
    record("warehouse in session", row[4] == WH, str(row[4]))
    record("database in session", row[5] == DB, str(row[5]))


def check_objects(cur) -> None:
    print("\n2. Foundation objects")
    # AM_TRANSFORMER has USAGE on all six schemas, so it can see all of them.
    use_role(cur, "AM_TRANSFORMER")
    run(cur, f"SHOW SCHEMAS IN DATABASE {DB}")
    found = {r[0] for r in run(cur, 'SELECT "name" FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))')}
    for s in SCHEMAS:
        record(f"schema {DB}.{s} exists", s in found)

    run(cur, f"SHOW WAREHOUSES LIKE '{WH}'")
    wh = run(cur, 'SELECT "size", "auto_suspend", "auto_resume" '
                  'FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))')
    record(f"warehouse {WH} exists", len(wh) == 1)
    if wh:
        size, suspend, resume = wh[0]
        record("warehouse size is X-Small", str(size).upper().replace("-", "") == "XSMALL", str(size))
        record("auto_suspend = 60", str(suspend) == "60", str(suspend))
        record("auto_resume = true", str(resume).lower() == "true", str(resume))

    run(cur, "SHOW ROLES LIKE 'AM_%'")
    roles = {r[0] for r in run(cur, 'SELECT "name" FROM TABLE(RESULT_SCAN(LAST_QUERY_ID()))')}
    for r in PROJECT_ROLES:
        record(f"role {r} exists", r in roles)

    # Informational only: tables are expected once Phase 3+ has run. (The Phase 2
    # version asserted zero, which was true only before ingestion.)
    rows = run(cur, f"""
        SELECT table_schema, COUNT(*) FROM {DB}.INFORMATION_SCHEMA.TABLES
        WHERE table_schema IN ({", ".join(f"'{s}'" for s in SCHEMAS)})
        GROUP BY 1 ORDER BY 1
    """)
    print("     project tables/views by schema: "
          + (", ".join(f"{s}={n}" for s, n in rows) or "none"))


def check_user_roles(cur) -> None:
    print("\n3. Service-user least privilege")
    rows = run(cur, "SELECT VALUE::STRING FROM TABLE(FLATTEN(PARSE_JSON(CURRENT_AVAILABLE_ROLES())))")
    available = {r[0] for r in rows}
    for r in FUNCTIONAL_ROLES:
        record(f"service user holds {r}", r in available)
    record("service user does NOT hold AM_ADMIN", "AM_ADMIN" not in available)
    record("service user does NOT hold ACCOUNTADMIN/SYSADMIN/SECURITYADMIN",
           not available & {"ACCOUNTADMIN", "SYSADMIN", "SECURITYADMIN", "USERADMIN"})


def check_privileges(cur) -> None:
    print("\n4. Privilege tests (temporary empty objects, dropped afterwards)")
    t = lambda schema: f"{DB}.{schema}.{CHECK}"  # noqa: E731

    # Ingestion layer
    expect(cur, "AM_INGESTOR", f"CREATE TABLE {t('RAW')} (check_id INT)", True, "create table in RAW")
    expect(cur, "AM_INGESTOR", f"CREATE TABLE {t('META')} (check_id INT)", True, "create table in META")
    for s in ("STAGING", "INTERMEDIATE", "CORE", "ANALYTICS"):
        expect(cur, "AM_INGESTOR", f"CREATE TABLE {t(s)} (check_id INT)", False, f"create table in {s}")

    # RAW/META readability flows through the future grants
    expect(cur, "AM_TRANSFORMER", f"SELECT COUNT(*) FROM {t('RAW')}", True, "read RAW (future grant)")
    expect(cur, "AM_TRANSFORMER", f"SELECT COUNT(*) FROM {t('META')}", True, "read META (future grant)")
    expect(cur, "AM_TRANSFORMER", f"INSERT INTO {t('RAW')} (check_id) SELECT 1 WHERE FALSE",
           False, "write to RAW")
    expect(cur, "AM_TRANSFORMER", f"CREATE TABLE {DB}.RAW.{CHECK}_X (check_id INT)", False,
           "create table in RAW")
    expect(cur, "AM_ANALYST", f"SELECT COUNT(*) FROM {t('RAW')}", False, "read RAW")

    # Transformation and curated layers
    for s in ("STAGING", "INTERMEDIATE", "CORE", "ANALYTICS"):
        expect(cur, "AM_TRANSFORMER", f"CREATE TABLE {t(s)} (check_id INT)", True, f"create table in {s}")
    expect(cur, "AM_TRANSFORMER",
           f"CREATE VIEW {DB}.ANALYTICS.{CHECK}_V AS SELECT 1 AS check_id", True,
           "create view in ANALYTICS")

    # Managed access: object owners cannot grant ad-hoc access
    expect(cur, "AM_TRANSFORMER", f"GRANT SELECT ON TABLE {t('CORE')} TO ROLE AM_INGESTOR", False,
           "grant on own object (managed access)")

    # Analyst read-only on curated layers
    expect(cur, "AM_ANALYST", f"SELECT COUNT(*) FROM {t('CORE')}", True, "read CORE (future grant)")
    expect(cur, "AM_ANALYST", f"SELECT COUNT(*) FROM {DB}.ANALYTICS.{CHECK}_V", True,
           "read ANALYTICS view (future grant)")
    expect(cur, "AM_ANALYST", f"SELECT COUNT(*) FROM {t('STAGING')}", False, "read STAGING")
    expect(cur, "AM_ANALYST", f"CREATE TABLE {DB}.ANALYTICS.{CHECK}_Y (check_id INT)", False,
           "create table in ANALYTICS")
    expect(cur, "AM_ANALYST", f"INSERT INTO {t('CORE')} (check_id) SELECT 1 WHERE FALSE", False,
           "write to CORE")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--show-identifiers", action="store_true",
                        help="print account and user unmasked")
    args = parser.parse_args()

    try:
        config = load_config()
    except SnowflakeConfigError as exc:
        print(f"Configuration error: {exc}")
        return 2

    print("Phase 2 Snowflake validation")
    with get_connection(config=config) as conn:
        cur = conn.cursor()
        try:
            check_context(cur, args.show_identifiers)
            check_objects(cur)
            check_user_roles(cur)
            check_privileges(cur)
        finally:
            print("\n5. Cleanup")
            cleanup(cur)
            use_role(cur, "AM_TRANSFORMER")
            leftover = run(cur, f"""
                SELECT COUNT(*) FROM {DB}.INFORMATION_SCHEMA.TABLES
                WHERE table_name LIKE '{CHECK}%'
            """)[0][0]
            record("all check objects dropped", leftover == 0, f"{leftover} remaining")

    failed = [r for r in results if not r.passed]
    print(f"\nSummary: {len(results) - len(failed)}/{len(results)} checks passed")
    return 0 if not failed else 1


if __name__ == "__main__":
    sys.exit(main())
