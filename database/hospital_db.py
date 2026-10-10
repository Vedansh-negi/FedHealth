import psycopg2
from config.database import DB_CONFIG


def get_hospital_connection(hospital_id):
    database_name = f"hospital_{hospital_id}_db"

    connection = psycopg2.connect(
        host=DB_CONFIG["host"],
        port=DB_CONFIG["port"],
        user=DB_CONFIG["user"],
        database=database_name
    )

    return connection