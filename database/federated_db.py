import psycopg2
from psycopg2.extensions import connection
from config.database import DB_CONFIG


def get_federated_connection() -> connection:
    """Create and return a connection to the federated database."""
    return psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        database="federated_db"
    )
