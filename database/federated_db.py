import psycopg2

from config.database import connection_kwargs


def get_federated_connection():
    return psycopg2.connect(**connection_kwargs("federated_db"))
