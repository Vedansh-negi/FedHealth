
import { useEffect, useState } from 'react'
import {
  Activity,
  Building2,
  Database,
  RefreshCw,
  Target,
} from 'lucide-react'

import {
  getDashboardData,
  getHospitals,
  getDatabaseHealth,
} from '../services/api'

export default function Reports() {
  const [summary, setSummary] = useState(null)
  const [hospitals, setHospitals] = useState([])
  const [databaseHealth, setDatabaseHealth] = useState(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function loadReports() {
    setLoading(true)
    setError('')

    try {
      const [dashboardData, hospitalData, healthData] =
        await Promise.all([
          getDashboardData(),
          getHospitals(),
          getDatabaseHealth(),
        ])

      setSummary(dashboardData)

      setHospitals(
        Array.isArray(hospitalData?.hospitals)
          ? hospitalData.hospitals
          : []
      )

      setDatabaseHealth(healthData)
    } catch (err) {
      setError(
        err.message || 'Reports load nahi ho paaye'
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadReports()
  }, [])

  const dashboardHospitals = Array.isArray(summary?.hospitals)
    ? summary.hospitals
    : []

  const hospitalStats = new Map(
    dashboardHospitals.map((hospital) => [
      hospital.hospital_id,
      hospital,
    ])
  )

  const totalPatients = dashboardHospitals.reduce(
    (total, hospital) =>
      total +
      (typeof hospital.patients === 'number'
        ? hospital.patients
        : 0),
    0
  )

  const totalDoctors = dashboardHospitals.reduce(
    (total, hospital) =>
      total +
      (typeof hospital.doctors === 'number'
        ? hospital.doctors
        : 0),
    0
  )

  const totalAppointments = dashboardHospitals.reduce(
    (total, hospital) =>
      total +
      (typeof hospital.appointments === 'number'
        ? hospital.appointments
        : 0),
    0
  )

  const reportMetrics = [
    {
      label: 'Registered Hospitals',
      value: hospitals.length,
      icon: Building2,
      color: 'blue',
    },
    {
      label: 'Patient Records',
      value: totalPatients.toLocaleString(),
      icon: Activity,
      color: 'green',
    },
    {
      label: 'Total Doctors',
      value: totalDoctors.toLocaleString(),
      icon: Target,
      color: 'purple',
    },
    {
      label: 'Appointments',
      value: totalAppointments.toLocaleString(),
      icon: Database,
      color: 'orange',
    },
  ]

  return (
    <div className="dashboard-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">SYSTEM REPORTS</p>

          <h1>Reports</h1>

          <p className="muted">
            FedHealth model performance, hospital and database summary.
          </p>
        </div>

        <button
          type="button"
          className="primary-button"
          onClick={loadReports}
          disabled={loading}
        >
          <RefreshCw size={17} />
          {loading ? 'Loading...' : 'Refresh Report'}
        </button>
      </div>

      {error && (
        <section className="panel">
          <h3>Unable to generate report</h3>
          <p className="muted">{error}</p>
        </section>
      )}

      {loading && !summary && (
        <p className="muted">Generating report...</p>
      )}

      {summary && (
        <>
          <section className="stats-grid">
            {reportMetrics.map(
              ({ label, value, icon: Icon, color }) => (
                <article className="stat-card" key={label}>
                  <div className={`stat-icon ${color}`}>
                    <Icon size={21} />
                  </div>

                  <p className="stat-label">{label}</p>

                  <h2>{value}</h2>

                  <p className="stat-note">
                    Latest backend records
                  </p>
                </article>
              )
            )}
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <h3>Hospital Summary</h3>

                <p className="muted">
                  Hospital records retrieved from the backend
                </p>
              </div>

              <Building2 size={21} />
            </div>

            {hospitals.length === 0 ? (
              <p className="muted">
                No hospital records available.
              </p>
            ) : (
              <div className="table-container">
                <table>
                  <thead>
                    <tr>
                      <th>Hospital</th>
                      <th>Database</th>
                      <th>Patients</th>
                      <th>Doctors</th>
                      <th>Appointments</th>
                    </tr>
                  </thead>

                  <tbody>
                    {hospitals.map((hospital) => {
                      const stats = hospitalStats.get(
                        hospital.hospital_id
                      )

                      return (
                        <tr key={hospital.hospital_id}>
                          <td>{hospital.hospital_name}</td>

                          <td>{hospital.database_name}</td>

                          <td>{stats?.patients ?? 0}</td>

                          <td>{stats?.doctors ?? 0}</td>

                          <td>{stats?.appointments ?? 0}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <h3>Database Health</h3>

                <p className="muted">
                  Database status reported by backend
                </p>
              </div>

              <Database size={21} />
            </div>

            {databaseHealth ? (
              <pre className="database-health">
                {JSON.stringify(databaseHealth, null, 2)}
              </pre>
            ) : (
              <p className="muted">
                Database health information unavailable.
              </p>
            )}
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <h3>Model Performance</h3>

                <p className="muted">
                  Federated model evaluation metrics
                </p>
              </div>

              <Target size={21} />
            </div>

            <p className="data-note">
              Accuracy, precision, recall, F1 score and completed
              federated rounds are not currently returned by the
              dashboard API. No performance values are fabricated.
            </p>
          </section>
        </>
      )}
    </div>
  )
}
