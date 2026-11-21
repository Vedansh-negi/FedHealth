"""Create the four PostgreSQL databases FedHealth needs (if missing).

Run from the project root:   python scripts/create_databases.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from psycopg2 import sql

from config.database import connection_kwargs

DATABASES = ["hospital_1_db", "hospital_2_db", "hospital_3_db", "federated_db"]


def main():
    conn = psycopg2.connect(**connection_kwargs("postgres"))
    conn.autocommit = True

    try:
        with conn.cursor() as cur:
            for name in DATABASES:
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s", (name,)
                )

                if cur.fetchone():
                    print(f"{name}: already exists")
                    continue

                cur.execute(
                    sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name))
                )
                print(f"{name}: created")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
