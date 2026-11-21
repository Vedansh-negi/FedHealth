import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import pandas as pd
import psycopg2
from psycopg2 import sql
from psycopg2.extras import execute_values

from config.database import connection_kwargs
from ml.model_config import FEATURE_COLUMNS, TARGET_COLUMN


CSV_PATH = "data/diabetes_binary_health_indicators_BRFSS2021.csv"


def connect_to_database(database_name):
    return psycopg2.connect(**connection_kwargs(database_name))


def create_hospital_tables(conn):
    with conn.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS patient_health_data (
                patient_id BIGINT PRIMARY KEY,
                highbp DOUBLE PRECISION NOT NULL,
                highchol DOUBLE PRECISION NOT NULL,
                cholcheck DOUBLE PRECISION NOT NULL,
                bmi DOUBLE PRECISION NOT NULL,
                smoker DOUBLE PRECISION NOT NULL,
                stroke DOUBLE PRECISION NOT NULL,
                heartdiseaseorattack DOUBLE PRECISION NOT NULL,
                physactivity DOUBLE PRECISION NOT NULL,
                fruits DOUBLE PRECISION NOT NULL,
                veggies DOUBLE PRECISION NOT NULL,
                hvyalcoholconsump DOUBLE PRECISION NOT NULL,
                anyhealthcare DOUBLE PRECISION NOT NULL,
                nodocbccost DOUBLE PRECISION NOT NULL,
                genhlth DOUBLE PRECISION NOT NULL,
                menthlth DOUBLE PRECISION NOT NULL,
                physhlth DOUBLE PRECISION NOT NULL,
                diffwalk DOUBLE PRECISION NOT NULL,
                sex DOUBLE PRECISION NOT NULL,
                age DOUBLE PRECISION NOT NULL,
                education DOUBLE PRECISION NOT NULL,
                income DOUBLE PRECISION NOT NULL,
                diabetes_binary INTEGER NOT NULL
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS training_runs (
                training_run_id SERIAL PRIMARY KEY,
                round_number INTEGER,
                model_version VARCHAR(100),
                sample_count INTEGER,
                accuracy DOUBLE PRECISION,
                precision_score DOUBLE PRECISION,
                recall_score DOUBLE PRECISION,
                f1_score DOUBLE PRECISION,
                loss DOUBLE PRECISION,
                training_time_seconds DOUBLE PRECISION,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                status VARCHAR(50)
            )
        """)

    conn.commit()


def load_dataset():
    print("Loading CSV dataset...")

    df = pd.read_csv(CSV_PATH)
    df.columns = df.columns.str.strip().str.lower()

    required_columns = FEATURE_COLUMNS + [TARGET_COLUMN]
    missing = sorted(set(required_columns) - set(df.columns))

    if missing:
        raise ValueError(f"CSV is missing required columns: {missing}")

    df = df[required_columns].copy()

    if df.isna().any().any():
        raise ValueError("CSV contains missing values; import stopped.")

    df[TARGET_COLUMN] = df[TARGET_COLUMN].astype(int)

    if not df[TARGET_COLUMN].isin([0, 1]).all():
        raise ValueError("Target column must contain only 0 and 1.")

    print(f"Dataset rows: {len(df):,}")
    return df


def split_into_hospitals(df):
    # Shuffle deterministically, then split without overlapping rows.
    df = df.sample(frac=1, random_state=42).reset_index(drop=True)

    n = len(df)
    first_split = n // 3
    second_split = (2 * n) // 3

    hospital_parts = [
        df.iloc[:first_split].reset_index(drop=True),
        df.iloc[first_split:second_split].reset_index(drop=True),
        df.iloc[second_split:].reset_index(drop=True),
    ]

    total = sum(len(part) for part in hospital_parts)
    if total != n:
        raise RuntimeError(
            f"Partition check failed: dataset has {n} rows, "
            f"but partitions have {total} rows."
        )

    print("Planned hospital record counts:")
    for hospital_id, part in enumerate(hospital_parts, start=1):
        print(f"  Hospital {hospital_id}: {len(part):,}")

    return hospital_parts


def main():
    df = load_dataset()
    hospital_parts = split_into_hospitals(df)

    # Preflight check all databases before inserting any records.
    connections = []

    try:
        for hospital_id in range(1, 4):
            database_name = f"hospital_{hospital_id}_db"
            conn = connect_to_database(database_name)
            connections.append((database_name, conn))

        for database_name, conn in connections:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                      AND table_name = 'patient_health_data'
                """)
                table_exists = cur.fetchone()[0] > 0

                if table_exists:
                    cur.execute(
                        "SELECT COUNT(*) FROM patient_health_data"
                    )
                    existing_count = cur.fetchone()[0]

                    if existing_count > 0:
                        raise RuntimeError(
                            f"{database_name} already has "
                            f"{existing_count:,} patient records. "
                            "No records were inserted. Do not rerun "
                            "until existing demo data is handled safely."
                        )

        for (database_name, conn), hospital_df in zip(
            connections, hospital_parts
        ):
            print(f"\nSetting up {database_name}...")
            create_hospital_tables(conn)

            columns = ["patient_id"] + FEATURE_COLUMNS + [TARGET_COLUMN]

            insert_query = sql.SQL(
                "INSERT INTO patient_health_data ({}) VALUES %s"
            ).format(
                sql.SQL(", ").join(
                    map(sql.Identifier, columns)
                )
            )

            records = [
                (index + 1, *row)
                for index, row in enumerate(
                    hospital_df.itertuples(index=False, name=None)
                )
            ]

            with conn.cursor() as cur:
                execute_values(
                    cur,
                    insert_query.as_string(conn),
                    records,
                    page_size=2000,
                )

            conn.commit()
            print(
                f"Imported {len(hospital_df):,} demo records "
                f"into {database_name}."
            )

    except Exception:
        for _, conn in connections:
            conn.rollback()
        raise

    finally:
        for _, conn in connections:
            conn.close()

    print("\nHospital database setup completed.")


if __name__ == "__main__":
    main()
