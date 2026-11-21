# FedHealth — Federated Learning for Healthcare

A healthcare-focused federated learning platform that demonstrates how multiple hospitals can collaboratively train a machine learning model while keeping their datasets distributed across separate hospital databases.

## Overview

FedHealth is a college Project-Based Learning (PBL) project combining federated machine learning, healthcare data management, database integration, and operating system resource monitoring.

Instead of combining all hospital datasets into one central dataset, the project simulates multiple hospital clients that participate in collaborative model training. A global model is updated using the clients' locally trained model parameters.

The project includes a web-based dashboard for exploring system metrics, hospital information, federated learning performance, database information, reports, and settings.

> **Note:** This is an educational demonstration using a public/simulated dataset. It is not intended for clinical diagnosis or real-world medical decision-making.

## Features

- **Hospital management:** patients, doctors, appointments, medical records, prescriptions, lab orders and lab reports, per hospital database.
- **Authentication and roles:** JWT login, bcrypt passwords, login throttling, role-based access (admin, doctor, nurse, receptionist, lab technician) and per-hospital data isolation.
- **Audit log:** every data change and every read of clinical records is recorded in the hospital's `audit_logs` table (admins can view it at `GET /api/audit-logs`).
- **Federated learning:** FedAvg-style training across three simulated hospitals; admins can start a round from the dashboard, and rounds, per-hospital updates and global model metrics are shown live.
- **AI prediction:** diabetes risk prediction for a patient using the latest federated global model (doctors and admins).
- **OS monitoring and database explorer:** admin-only system metrics, history, table list and row counts.
- **Model evaluation:** accuracy, precision, recall, F1-score and ROC-AUC on validation splits.

## Technology Stack

| Component | Technologies |
|---|---|
| Frontend | React, Vite, JavaScript, CSS |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| Machine Learning | Python, scikit-learn |
| Federated Learning | Local model training and FedAvg-style aggregation |
| API Communication | REST API |
| Development Environment | macOS, Node.js, Python, PostgreSQL |

## Project Architecture

```text
                 +----------------------+
                 |   React Web UI       |
                 |   (Vite Frontend)    |
                 +----------+-----------+
                            |
                         REST API
                            |
                 +----------v-----------+
                 |    FastAPI Backend   |
                 +----------+-----------+
                            |
          +-----------------+-----------------+
          |                 |                 |
  +-------v-------+ +-------v-------+ +-------v-------+
  | Hospital 1    | | Hospital 2    | | Hospital 3    |
  | Local Data    | | Local Data    | | Local Data    |
  | Local Model   | | Local Model   | | Local Model   |
  +-------+-------+ +-------+-------+ +-------+-------+
          |                 |                 |
          +-----------------+-----------------+
                            |
                 +----------v-----------+
                 | Global Model Update  |
                 | FedAvg-style Demo    |
                 +----------------------+
```

The architecture illustrates the intended workflow. The current project is an educational prototype, and its hospital clients and training workflow should not be interpreted as a production-grade healthcare deployment.

## Federated Learning Workflow

1. Prepare the dataset for model training and evaluation.
2. Distribute or organize training data across simulated hospital clients.
3. Train local models using each client's local data.
4. Aggregate the local model updates to update the global model.
5. Evaluate the global model using classification metrics.
6. Display relevant performance information in the dashboard.

Federated learning is designed to reduce the need to centralize raw training data. This prototype demonstrates the concept; it does not by itself guarantee privacy or regulatory compliance.

## Model Evaluation

The following are the recorded validation-split results from the current project run:

| Metric | Result |
|---|---:|
| Accuracy | 70.65% |
| Precision | 28.95% |
| Recall | 73.41% |
| F1-score | 41.53% |
| ROC-AUC | Approximately 0.7873 |

**Important:** These results are from a validation split, not a confirmed independent test set. They are preliminary educational results and do not establish clinical usefulness. Precision, recall, class distribution, and the evaluation methodology should be considered when interpreting performance.

## Project Structure

```text
FedHealth/
├── backend/
│   ├── app/
│   │   ├── api/routes/     # auth, patients, doctors, appointments, records, prescriptions,
│   │   │                   # lab orders/reports, ai predictions, dashboard, hospitals,
│   │   │                   # federated, database explorer, os monitoring, audit
│   │   ├── core/           # security (JWT, roles, hospital scope) and audit logging
│   │   └── main.py
│   ├── tests/
│   └── requirements.txt
├── config/                 # environment-based database settings
├── database/               # connection helpers
├── frontend/               # React + Vite dashboard
├── ml/                     # local training, FedAvg, evaluation, centralized baseline
├── os_layer/               # resource monitor and OS concept demos
├── scripts/                # database creation, schema setup, data load, admin creation
├── .env.example
└── reset_user_password.py
```

## Prerequisites

Install the following before running the project:

- Python 3
- Node.js and npm
- PostgreSQL 16
- Git

The commands below assume macOS and that PostgreSQL has been installed and configured locally.

## Installation and Setup

### 1. Get the code and configure

```bash
git clone https://github.com/krish-08-s/FedHealth.git
cd FedHealth
cp .env.example .env      # then edit .env
```

In `.env` set your PostgreSQL user/password and a JWT secret
(`python -c "import secrets; print(secrets.token_urlsafe(48))"`).
If `FEDHEALTH_JWT_SECRET` is empty a random secret is used, which logs everyone out whenever the server restarts.

### 2. Python environment

```bash
python3 -m venv backend/venv
source backend/venv/bin/activate
pip install -r backend/requirements.txt
```

### 3. Create and initialise the databases

PostgreSQL must be running (`brew services start postgresql@16` on macOS). Then, from the project root:

```bash
python scripts/create_databases.py             # hospital_1_db, hospital_2_db, hospital_3_db, federated_db
python scripts/init_hospital_management_schema.py
python scripts/init_database.py                # loads the demo diabetes dataset, split across 3 hospitals (run once)
python scripts/init_federated_schema.py
```

### 4. Create a login

```bash
python scripts/create_admin.py --hospital 1 --email admin@example.com --name "Admin" --role admin
```

Repeat with `--hospital 2` / `--hospital 3` or other roles
(`doctor`, `nurse`, `receptionist`, `lab_technician`). The password is entered at a hidden prompt.
Doctors can also be created from the Doctors page by an admin. To reset a password: `python reset_user_password.py <hospital_id>`.

### 5. Start the backend

From the project root:

```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```

API docs: `http://localhost:8000/docs`

### 6. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` and sign in (choose the same hospital the user was created in).

### 7. Train the federated model

Sign in as an admin, open **Federated Learning** and click **Run Training Round**
(or run `python -m ml.federated_learning` then `python -m ml.evaluate_global_model` from the project root).
Metrics then appear on the Dashboard and Federated Learning pages.
`python -m ml.centralized_training` (baseline comparison) additionally needs a held-out CSV at
`data/common_test.csv` (or the path in `FEDHEALTH_TEST_DATA`).

### Tests

```bash
cd backend && python -m pytest tests
```

## Access Rules

| Area | admin | doctor | nurse | receptionist | lab technician |
|---|---|---|---|---|---|
| Patients, appointments (read) | yes | yes | yes | yes | yes |
| Patients, appointments (create/edit) | yes | yes | yes | yes | no |
| Doctors (create/edit/delete) | yes | no | no | no | no |
| Medical records | yes | yes | yes | no | no |
| Prescriptions (read) | yes | yes | yes | no | no |
| Prescriptions (create/edit) | yes | yes | no | no | no |
| Lab orders | yes | yes | yes | no | yes |
| Lab reports (read) | yes | yes | yes | no | yes |
| Lab reports (create/edit) | yes | yes | no | no | yes |
| AI prediction | yes | yes | no | no | no |
| Federated learning (view) | yes | yes | no | no | no |
| Start training, OS monitoring, DB explorer, audit log, settings | yes | no | no | no | no |
| Deleting clinical records | yes | no | no | no | no |

Every request is also limited to the hospital the user logged in to.
Dashboard counts and the hospital list show aggregate numbers only.

## Privacy and Security

- Use public or synthetic data for demonstrations.
- Do not commit real patient records, database passwords, API keys, or other secrets.
- Keep environment-specific configuration outside version control.
- Federated learning alone does not guarantee privacy; additional controls may be required for real deployments.

## Limitations

- Educational prototype, not a production healthcare platform and not validated for clinical use or regulatory compliance.
- Hospital clients are simulated: all three hospital databases live on one PostgreSQL server and one backend process trains all clients.
- Model results are validation-split results on a public dataset, not an independent test.
- Login throttling is in-memory and resets when the server restarts; tokens live in the browser's localStorage.
- Federated learning alone does not guarantee privacy; differential privacy and secure aggregation are not implemented.

## Future Improvements

- Per-hospital user directory management screens and an audit-log viewer in the UI.
- Independent test-set evaluation and wider model comparison.
- Differential privacy and secure aggregation.
- Billing, pharmacy/inventory and ward/bed management modules.
- Deployment documentation (Docker, HTTPS, httpOnly cookie sessions).

## Author

**Krish Ruhela**

GitHub: [@krish-08-s](https://github.com/krish-08-s)

## License

No license has been specified yet. Unless a license is added to this repository, reuse and redistribution are not automatically granted.
