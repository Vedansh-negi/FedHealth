"""Reset a user's password.  Usage: python reset_user_password.py [hospital_id]"""

import getpass
import sys

from backend.app.core.security import hash_password
from database.hospital_db import get_hospital_connection

hospital_id = int(sys.argv[1]) if len(sys.argv) > 1 else 1

email = input("Enter user email: ").strip().lower()
new_password = getpass.getpass("Enter new password (min 8 characters): ")

if len(new_password) < 8:
    sys.exit("Password must be at least 8 characters.")

connection = get_hospital_connection(hospital_id)

try:
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE email = %s",
            (hash_password(new_password), email)
        )

        if cursor.rowcount == 0:
            print("User not found")
        else:
            connection.commit()
            print("Password reset successful")

finally:
    connection.close()
