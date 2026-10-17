import psycopg2
from psycopg2.extensions import connection as PGConnection
from config.database import DB_CONFIG


def get_hospital_connection(hospital_id: int) -> PGConnection:
    """Create and return a connection to the specified hospital database."""

    database_name = f"hospital_{hospital_id}_db"

    return psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        database=database_name
    )
