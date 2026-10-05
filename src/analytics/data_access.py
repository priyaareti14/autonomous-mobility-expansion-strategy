"""Read-only access to the dbt warehouse for Phase 5.

Uses AM_TRANSFORMER, which can read INTERMEDIATE (the candidate mapping tables) as
well as CORE and ANALYTICS. Phase 5 only SELECTs: it writes nothing to Snowflake.
"""

from __future__ import annotations

import pandas as pd

from src.utils.snowflake_connection import get_connection

DB = "AUTONOMOUS_MOBILITY"


class Warehouse:
    def __init__(self, role: str = "AM_TRANSFORMER"):
        self.conn = get_connection(role=role)
        cur = self.conn.cursor()
        cur.execute("USE SECONDARY ROLES NONE")
        self._cache: dict[str, pd.DataFrame] = {}

    def query(self, sql: str) -> pd.DataFrame:
        cur = self.conn.cursor()
        cur.execute(sql)
        df = cur.fetch_pandas_all()
        df.columns = [c.lower() for c in df.columns]
        return df

    def table(self, schema: str, name: str, columns: str = "*") -> pd.DataFrame:
        key = f"{schema}.{name}.{columns}"
        if key not in self._cache:
            self._cache[key] = self.query(f"select {columns} from {DB}.{schema}.{name}")
        return self._cache[key]

    def close(self) -> None:
        self.conn.close()
