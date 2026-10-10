import psycopg2

conn = psycopg2.connect(
    host="localhost",
    port=5432,
    database="hospital_1_db",
    user="vedanshnegi"
)

cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM patient_health_data;")

count = cursor.fetchone()[0]

print("Hospital 1 records:", count)

cursor.close()
conn.close()