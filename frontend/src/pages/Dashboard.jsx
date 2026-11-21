
import { useEffect, useState } from 'react'
import {
  Activity,
  Building2,
  Network,
  Target,
  TrendingUp,
} from 'lucide-react'

import {
  getDashboardData,
  getHospitals,
} from '../services/api'

function Dashboard() {
  const [summary, setSummary] = useState(null)
  const [hospitalData, setHospitalData] = useState(null)

  const [apiError, setApiError] = useState('')
  const [hospitalError, setHospitalError] = useState('')

  useEffect(() => {
    let cancelled = false

    async function loadDashboard() {
      try {
        const data = await getDashboardData()

        if (!cancelled) {
          setSummary(data)
        }
      } catch (error) {
        if (!cancelled) {
          setApiError(error.message)
        }
      }
    }

    async function loadHospitals() {
      try {
        const data = await getHospitals()

        if (!cancelled) {
          setHospitalData(data)
        }
      } catch (error) {
        if (!cancelled) {
          setHospitalError(error.message)
        }
      }
    }

    loadDashboard()
    loadHospitals()

    return () => {
      cancelled = true
    }
  }, [])

  if (apiError) {
    return (
      <section className="panel">
        <h2>Unable to load dashboard</h2>

        <p className="muted">{apiError}</p>

        <p className="muted">
          Check that the FastAPI backend is running on port 8000.
        </p>
      </section>
    )
  }

  if (!summary) {
    return <p className="muted">Loading dashboard data...</p>
  }

  const formatPercent = (value) =>
    typeof value === 'number'
      ? `${(value * 100).toFixed(2)}%`
      : 'Not available'

  const dashboardHospitals = Array.isArray(summary.hospitals)
    ? summary.hospitals
    : []

  const hospitalList = Array.isArray(hospitalData?.hospitals)
    ? hospitalData.hospitals
    : []

  const hospitalStats = new Map(
    dashboardHospitals.map((hospital) => [
      hospital.hospital_id,
      hospital,
    ]),
  )

  const totalHospitals =
    typeof hospitalData?.total_hospitals === 'number'
      ? hospitalData.total_hospitals
      : hospitalList.length

  const totalPatients = dashboardHospitals.reduce(
    (total, hospital) =>
      total +
      (typeof hospital.patients === 'number'
        ? hospital.patients
        : 0),
    0,
  )

  const totalDoctors = dashboardHospitals.reduce(
    (total, hospital) =>
      total +
      (typeof hospital.doctors === 'number'
        ? hospital.doctors
        : 0),
    0,
  )

  const totalAppointments = dashboardHospitals.reduce(
    (total, hospital) =>
      total +
      (typeof hospital.appointments === 'number'
        ? hospital.appointments
        : 0),
    0,
  )

  const latestModel = summary.latest_model

  const stats = [
    {
      label: 'Registered Hospitals',
      value: String(totalHospitals),
      note: 'Participating institutions',
      icon: Building2,
      color: 'blue',
    },
    {
      label: 'Federated Rounds',
      value:
        typeof summary.federated_rounds === 'number'
          ? String(summary.federated_rounds)
          : 'Not available',
      note: 'Completed training rounds',
      icon: Network,
      color: 'purple',
    },
    {
      label: 'Global Model Accuracy',
      value: formatPercent(latestModel?.accuracy),
      note: latestModel?.evaluated
        ? `Validation split · ${latestModel.model_version}`
        : 'Run training and evaluation to see metrics',
      icon: Target,
      color: 'green',
    },
    {
      label: 'System Status',
      value: 'API connected',
      note: 'Dashboard API response received',
      icon: Activity,
      color: 'orange',
    },
  ]

  const metrics = [
    { label: 'Accuracy', value: latestModel?.accuracy },
    { label: 'Precision', value: latestModel?.precision },
    { label: 'Recall', value: latestModel?.recall },
    { label: 'F1 Score', value: latestModel?.f1_score },
  ]

  return (
    <div className="dashboard-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">OVERVIEW</p>

          <h1>Dashboard</h1>

          <p className="muted">
            Monitor federated learning and healthcare system activity.
          </p>
        </div>

        <span className="date-chip">
          FedHealth Prototype
        </span>
      </div>

      <section className="stats-grid">
        {stats.map(({ label, value, note, icon: Icon, color }) => (
          <article className="stat-card" key={label}>
            <div className={`stat-icon ${color}`}>
              <Icon size={21} />
            </div>

            <p className="stat-label">{label}</p>

            <h2>{value}</h2>

            <p className="stat-note">{note}</p>
          </article>
        ))}
      </section>

      <section className="content-grid">
        <article className="panel performance-panel">
          <div className="panel-heading">
            <div>
              <h3>Model Performance</h3>

              <p className="muted">
                Saved global model evaluation metrics
              </p>
            </div>

            <TrendingUp size={21} />
          </div>

          {metrics.map((metric) => (
            <div className="metric-row" key={metric.label}>
              <div className="metric-label">
                <span>{metric.label}</span>

                <strong>
                  {formatPercent(metric.value)}
                </strong>
              </div>

              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{
                    width:
                      typeof metric.value === 'number'
                        ? `${Math.min(metric.value * 100, 100)}%`
                        : '0%',
                  }}
                />
              </div>
            </div>
          ))}

          <p className="data-note">
            {latestModel?.evaluated
              ? 'Metrics are from a validation split of the hospitals\' local data, not an independent test set. They are not clinical validation.'
              : 'No evaluated global model yet. Metrics appear after a federated round has been trained and evaluated.'}
          </p>
        </article>

        <article className="panel">
          <div className="panel-heading">
            <div>
              <h3>Hospital Network</h3>

              <p className="muted">
                Live records from the backend API
              </p>
            </div>

            <Building2 size={21} />
          </div>

          {hospitalError && (
            <p className="muted">
              Unable to load hospital records: {hospitalError}
            </p>
          )}

          {!hospitalError && !hospitalData && (
            <p className="muted">
              Loading hospital records...
            </p>
          )}

          {!hospitalError &&
            hospitalData &&
            hospitalList.length === 0 && (
              <p className="muted">
                No hospital records available.
              </p>
            )}

          <div className="hospital-list">
            {hospitalList.map((hospital) => {
              const stats = hospitalStats.get(
                hospital.hospital_id,
              )

              const patients = stats?.patients ?? 0
              const doctors = stats?.doctors ?? 0
              const appointments = stats?.appointments ?? 0

              return (
                <div
                  className="hospital-row"
                  key={hospital.hospital_id}
                >
                  <div className="hospital-avatar">
                    <Building2 size={19} />
                  </div>

                  <div className="hospital-info">
                    <strong>
                      {hospital.hospital_name}
                    </strong>

                    <span>
                      {hospital.database_name}
                    </span>

                    <span>
                      {patients} patients · {doctors} doctors ·{' '}
                      {appointments} appointments
                    </span>
                  </div>

                  <span className="status-badge">
                    Configured
                  </span>
                </div>
              )
            })}
          </div>

          {!hospitalError && hospitalData && (
            <p className="data-note">
              Total hospitals: {totalHospitals}. Total patient
              records: {totalPatients.toLocaleString()}.
              Total doctors: {totalDoctors.toLocaleString()}.
              Total appointments:{' '}
              {totalAppointments.toLocaleString()}.
            </p>
          )}
        </article>
      </section>
    </div>
  )
}

export default Dashboard
