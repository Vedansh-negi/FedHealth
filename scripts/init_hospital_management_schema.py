import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import psycopg2

from config.database import connection_kwargs


HOSPITAL_DATABASES = [
    "hospital_1_db",
    "hospital_2_db",
    "hospital_3_db",
]


def connect_to_database(database_name):
    """
    Connect to an existing hospital database.
    Uses the same DB_CONFIG pattern as database/hospital_db.py.
    """
    return psycopg2.connect(**connection_kwargs(database_name))


def create_hospital_management_tables(conn):
    with conn.cursor() as cur:

        # 1. Departments
        cur.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                department_id SERIAL PRIMARY KEY,
                department_name VARCHAR(100) NOT NULL UNIQUE,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Users
        cur.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id SERIAL PRIMARY KEY,
                full_name VARCHAR(150) NOT NULL,
                email VARCHAR(150) NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role VARCHAR(30) NOT NULL CHECK (
                    role IN (
                        'admin',
                        'doctor',
                        'nurse',
                        'receptionist',
                        'lab_technician'
                    )
                ),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 3. Doctors
        cur.execute("""
            CREATE TABLE IF NOT EXISTS doctors (
                doctor_id SERIAL PRIMARY KEY,
                user_id INTEGER UNIQUE
                    REFERENCES users(user_id),
                department_id INTEGER
                    REFERENCES departments(department_id),
                specialization VARCHAR(100),
                qualification VARCHAR(150),
                license_number VARCHAR(100) UNIQUE,
                consultation_fee NUMERIC(10,2) DEFAULT 0
            )
        """)

        # 4. Patients
        cur.execute("""
            CREATE TABLE IF NOT EXISTS patients (
                patient_id BIGSERIAL PRIMARY KEY,
                patient_number VARCHAR(50) NOT NULL UNIQUE,
                full_name VARCHAR(150) NOT NULL,
                date_of_birth DATE,
                gender VARCHAR(20),
                phone VARCHAR(20),
                email VARCHAR(150),
                address TEXT,
                blood_group VARCHAR(5),
                emergency_contact_name VARCHAR(150),
                emergency_contact_phone VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 5. Appointments
        cur.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                appointment_id BIGSERIAL PRIMARY KEY,
                patient_id BIGINT NOT NULL
                    REFERENCES patients(patient_id),
                doctor_id INTEGER NOT NULL
                    REFERENCES doctors(doctor_id),
                appointment_date DATE NOT NULL,
                appointment_time TIME NOT NULL,
                reason TEXT,
                status VARCHAR(30) NOT NULL DEFAULT 'scheduled'
                    CHECK (
                        status IN (
                            'scheduled',
                            'confirmed',
                            'completed',
                            'cancelled',
                            'no_show'
                        )
                    ),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 6. Medical Records / EHR
        cur.execute("""
            CREATE TABLE IF NOT EXISTS medical_records (
                record_id BIGSERIAL PRIMARY KEY,
                patient_id BIGINT NOT NULL
                    REFERENCES patients(patient_id),
                doctor_id INTEGER
                    REFERENCES doctors(doctor_id),
                appointment_id BIGINT
                    REFERENCES appointments(appointment_id),
                diagnosis TEXT,
                clinical_notes TEXT,
                blood_pressure VARCHAR(20),
                heart_rate INTEGER,
                temperature NUMERIC(5,2),
                oxygen_saturation NUMERIC(5,2),
                height_cm NUMERIC(6,2),
                weight_kg NUMERIC(6,2),
                recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 7. Prescriptions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS prescriptions (
                prescription_id BIGSERIAL PRIMARY KEY,
                record_id BIGINT NOT NULL
                    REFERENCES medical_records(record_id),
                patient_id BIGINT NOT NULL
                    REFERENCES patients(patient_id),
                doctor_id INTEGER
                    REFERENCES doctors(doctor_id),
                medicine_name VARCHAR(150) NOT NULL,
                dosage VARCHAR(100),
                frequency VARCHAR(100),
                duration VARCHAR(100),
                instructions TEXT,
                prescribed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 8. Lab Orders
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lab_orders (
                lab_order_id BIGSERIAL PRIMARY KEY,
                patient_id BIGINT NOT NULL
                    REFERENCES patients(patient_id),
                doctor_id INTEGER
                    REFERENCES doctors(doctor_id),
                test_name VARCHAR(150) NOT NULL,
                priority VARCHAR(20) DEFAULT 'normal'
                    CHECK (
                        priority IN ('normal', 'urgent')
                    ),
                status VARCHAR(30) DEFAULT 'ordered'
                    CHECK (
                        status IN (
                            'ordered',
                            'sample_collected',
                            'in_progress',
                            'completed',
                            'cancelled'
                        )
                    ),
                ordered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 9. Lab Reports
        cur.execute("""
            CREATE TABLE IF NOT EXISTS lab_reports (
                lab_report_id BIGSERIAL PRIMARY KEY,
                lab_order_id BIGINT NOT NULL UNIQUE
                    REFERENCES lab_orders(lab_order_id),
                result_value TEXT,
                result_unit VARCHAR(50),
                reference_range VARCHAR(100),
                remarks TEXT,
                reported_by INTEGER
                    REFERENCES users(user_id),
                reported_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 10. AI Predictions
        cur.execute("""
            CREATE TABLE IF NOT EXISTS ai_predictions (
                prediction_id BIGSERIAL PRIMARY KEY,
                patient_id BIGINT NOT NULL
                    REFERENCES patients(patient_id),
                model_name VARCHAR(100) NOT NULL,
                model_version VARCHAR(100),
                prediction_result JSONB NOT NULL,
                confidence_score NUMERIC(6,5),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 11. Audit Logs
        cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                audit_id BIGSERIAL PRIMARY KEY,
                user_id INTEGER
                    REFERENCES users(user_id),
                action VARCHAR(100) NOT NULL,
                entity_type VARCHAR(100),
                entity_id VARCHAR(100),
                details JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Indexes
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_patients_name
            ON patients(full_name)
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_appointments_patient_date
            ON appointments(patient_id, appointment_date)
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_appointments_doctor_date
            ON appointments(doctor_id, appointment_date)
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_medical_records_patient
            ON medical_records(patient_id)
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_prescriptions_patient
            ON prescriptions(patient_id)
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_lab_orders_patient
            ON lab_orders(patient_id)
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_ai_predictions_patient
            ON ai_predictions(patient_id)
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at
            ON audit_logs(created_at)
        """)


def initialize_database(database_name):
    conn = None

    try:
        print(f"\nConnecting to {database_name}...")

        conn = connect_to_database(database_name)

        create_hospital_management_tables(conn)

        conn.commit()

        print(
            f"Hospital management tables created successfully "
            f"in {database_name}"
        )

    except Exception as exc:
        if conn:
            conn.rollback()

        print(
            f"Failed to initialize {database_name}: {exc}"
        )

        raise

    finally:
        if conn:
            conn.close()


def main():
    print("Starting FedHealth hospital management schema setup...")

    for database_name in HOSPITAL_DATABASES:
        initialize_database(database_name)

    print("\nAll hospital databases initialized successfully.")


if __name__ == "__main__":
    main()
