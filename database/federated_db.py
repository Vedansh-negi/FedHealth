
import psycopg2
from config.database import DB_CONFIG


def get_federated_connection():
    return psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        database="federated_db"
    )
