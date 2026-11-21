import psycopg2

from config.database import connection_kwargs

HOSPITAL_IDS = (1, 2, 3)


def get_hospital_connection(hospital_id):
    if hospital_id not in HOSPITAL_IDS:
        raise ValueError(f"Unknown hospital id: {hospital_id}")

    return psycopg2.connect(**connection_kwargs(f"hospital_{hospital_id}_db"))
