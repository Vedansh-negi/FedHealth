"""Database connection settings, read from environment variables.

Copy ``.env.example`` to ``.env`` (project root) and adjust. The values
below are only local-development defaults; no password is hardcoded.
"""


import os

from config.env import load_env

load_env()

DB_CONFIG = {
    "host": os.getenv("FEDHEALTH_DB_HOST", "localhost"),
    "port": int(os.getenv("FEDHEALTH_DB_PORT", "5432")),
    "user": os.getenv("FEDHEALTH_DB_USER", "krish"),
    "password": os.getenv("FEDHEALTH_DB_PASSWORD", ""),
}


def connection_kwargs(database_name):
    """Keyword arguments for psycopg2.connect()."""
    kwargs = {
        "host": DB_CONFIG["host"],
        "port": DB_CONFIG["port"],
        "user": DB_CONFIG["user"],
        "database": database_name,
        "connect_timeout": 5,
    }
    if DB_CONFIG["password"]:
        kwargs["password"] = DB_CONFIG["password"]
    return kwargs
