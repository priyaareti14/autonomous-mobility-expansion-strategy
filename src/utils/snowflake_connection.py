"""Snowflake connection helper for the Autonomous Mobility Expansion project.

Configuration comes from environment variables, optionally loaded from a
git-ignored ``.env`` file at the repository root. Authentication is key-pair
only (``SNOWFLAKE_JWT``). No credentials are embedded here, and no secret
values are logged.

Required variables:
    SNOWFLAKE_ACCOUNT            account identifier, e.g. ``orgname-accountname``
    SNOWFLAKE_USER               service user name
    SNOWFLAKE_PRIVATE_KEY_PATH   path to the encrypted PKCS#8 private key,
                                 which must live OUTSIDE the repository

Optional variables:
    SNOWFLAKE_PRIVATE_KEY_PASSPHRASE   passphrase for the private key
    SNOWFLAKE_ROLE                     default AM_ANALYST (least privilege)
    SNOWFLAKE_WAREHOUSE                default AM_EXPANSION_WH
    SNOWFLAKE_DATABASE                 default AUTONOMOUS_MOBILITY
    SNOWFLAKE_SCHEMA                   no default
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import snowflake.connector
from dotenv import load_dotenv
from snowflake.connector import SnowflakeConnection

REPO_ROOT = Path(__file__).resolve().parents[2]

REQUIRED_VARS = (
    "SNOWFLAKE_ACCOUNT",
    "SNOWFLAKE_USER",
    "SNOWFLAKE_PRIVATE_KEY_PATH",
)

DEFAULT_ROLE = "AM_ANALYST"
DEFAULT_WAREHOUSE = "AM_EXPANSION_WH"
DEFAULT_DATABASE = "AUTONOMOUS_MOBILITY"


class SnowflakeConfigError(RuntimeError):
    """Raised when connection configuration is missing or unsafe."""


@dataclass(frozen=True)
class SnowflakeConfig:
    account: str
    user: str
    private_key_path: Path
    private_key_passphrase: str | None
    role: str
    warehouse: str
    database: str
    schema: str | None

    def __repr__(self) -> str:  # never expose the passphrase
        return (
            f"SnowflakeConfig(user={self.user!r}, role={self.role!r}, "
            f"warehouse={self.warehouse!r}, database={self.database!r}, "
            f"schema={self.schema!r}, private_key_path=<set>, "
            f"private_key_passphrase={'<set>' if self.private_key_passphrase else None})"
        )


def load_config(env_file: Path | None = None) -> SnowflakeConfig:
    """Build the configuration from the environment (and ``.env`` if present).

    Variables already set in the process environment take precedence over
    values in ``.env``.
    """
    load_dotenv(env_file or REPO_ROOT / ".env", override=False)

    missing = [name for name in REQUIRED_VARS if not os.getenv(name, "").strip()]
    if missing:
        raise SnowflakeConfigError(
            "Missing required Snowflake configuration: "
            + ", ".join(missing)
            + ". Copy .env.example to .env and fill in the values."
        )

    key_path = Path(os.environ["SNOWFLAKE_PRIVATE_KEY_PATH"]).expanduser().resolve()
    if not key_path.is_file():
        raise SnowflakeConfigError(
            "SNOWFLAKE_PRIVATE_KEY_PATH does not point to an existing file."
        )
    if key_path.is_relative_to(REPO_ROOT):
        raise SnowflakeConfigError(
            "The private key is inside the repository. Move it outside the repo "
            "and update SNOWFLAKE_PRIVATE_KEY_PATH."
        )

    return SnowflakeConfig(
        account=os.environ["SNOWFLAKE_ACCOUNT"].strip(),
        user=os.environ["SNOWFLAKE_USER"].strip(),
        private_key_path=key_path,
        private_key_passphrase=os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE") or None,
        role=os.getenv("SNOWFLAKE_ROLE") or DEFAULT_ROLE,
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE") or DEFAULT_WAREHOUSE,
        database=os.getenv("SNOWFLAKE_DATABASE") or DEFAULT_DATABASE,
        schema=os.getenv("SNOWFLAKE_SCHEMA") or None,
    )


def get_connection(
    role: str | None = None,
    config: SnowflakeConfig | None = None,
) -> SnowflakeConnection:
    """Open a key-pair-authenticated Snowflake connection.

    ``role`` overrides the configured role for this connection only.
    The caller is responsible for closing the connection (use it as a
    context manager).
    """
    cfg = config or load_config()
    params = {
        "account": cfg.account,
        "user": cfg.user,
        "authenticator": "SNOWFLAKE_JWT",
        "private_key_file": str(cfg.private_key_path),
        "role": role or cfg.role,
        "warehouse": cfg.warehouse,
        "database": cfg.database,
        "application": "autonomous-mobility-expansion",
    }
    if cfg.private_key_passphrase:
        params["private_key_file_pwd"] = cfg.private_key_passphrase
    if cfg.schema:
        params["schema"] = cfg.schema
    return snowflake.connector.connect(**params)
