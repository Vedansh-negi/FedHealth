"""Create (or reset) a staff login in one hospital database.

Run from the project root:

    python scripts/create_admin.py --hospital 1 --email admin@hospital1.test \
        --name "Hospital 1 Admin" --role admin

The password is typed in a hidden prompt, never passed on the command line.
"""

import argparse
import getpass
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.app.core.security import ALL_ROLES, hash_password
from database.hospital_db import get_hospital_connection


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--hospital", type=int, choices=(1, 2, 3), required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--role", choices=ALL_ROLES, default="admin")
    args = parser.parse_args()

    password = getpass.getpass("Password (min 8 characters): ")

    if len(password) < 8:
        sys.exit("Password must be at least 8 characters.")

    if password != getpass.getpass("Repeat password: "):
        sys.exit("Passwords do not match.")

    conn = get_hospital_connection(args.hospital)

    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (full_name, email, password_hash, role, is_active)
                VALUES (%s, %s, %s, %s, TRUE)
                ON CONFLICT (email) DO UPDATE
                SET password_hash = EXCLUDED.password_hash,
                    role = EXCLUDED.role,
                    full_name = EXCLUDED.full_name,
                    is_active = TRUE
                RETURNING user_id
                """,
                (
                    args.name.strip(),
                    args.email.strip().lower(),
                    hash_password(password),
                    args.role,
                ),
            )
            user_id = cur.fetchone()[0]

        conn.commit()
        print(f"Saved {args.role} user #{user_id} in hospital {args.hospital}.")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
