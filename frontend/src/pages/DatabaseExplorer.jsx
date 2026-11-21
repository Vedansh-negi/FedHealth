
import { useEffect, useState } from 'react'
import {
  Database,
  RefreshCw,
  HardDrive,
  Users,
  Activity,
} from 'lucide-react'

import {
  getDatabaseHealth,
  getDatabaseInfo,
} from '../services/api'

export default function DatabaseExplorer() {
  const [databaseHealth, setDatabaseHealth] = useState(null)
  const [databaseInfo, setDatabaseInfo] = useState(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function loadDatabases() {
    setLoading(true)
    setError('')

    try {
      const [healthData, infoData] = await Promise.all([
        getDatabaseHealth(),
        getDatabaseInfo(),
      ])

      setDatabaseHealth(healthData)
      setDatabaseInfo(infoData)
    } catch (err) {
      setError(
        err.message || 'Database details load nahi ho paaye'
      )
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadDatabases()
  }, [])

  const databases = Array.isArray(databaseInfo?.databases)
    ? databaseInfo.databases
    : Array.isArray(databaseInfo)
      ? databaseInfo
      : []

  const connectedCount = databases.filter(
    (db) =>
      db.status === 'Connected' ||
      db.status === 'connected'
  ).length

  const tableCount = databases.reduce(
    (total, db) =>
      total +
      (typeof db.table_count === 'number'
        ? db.table_count
        : Array.isArray(db.tables)
          ? db.tables.length
          : 0),
    0
  )

  const patientCount = databases.reduce(
    (total, db) =>
      total +
      (Array.isArray(db.tables)
        ? db.tables.reduce(
            (sum, table) =>
              sum +
              (table.name === 'patient_health_data'
                ? table.row_count || 0
                : 0),
            0
          )
        : 0),
    0
  )

  return (
    <div className="dashboard-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">DATABASE MANAGEMENT</p>

          <h1>Database Explorer</h1>

          <p className="muted">
            View PostgreSQL database connections, tables and record counts.
          </p>
        </div>

        <button
          type="button"
          className="primary-button"
          onClick={loadDatabases}
          disabled={loading}
        >
          <RefreshCw size={17} />
          {loading ? 'Loading...' : 'Refresh Databases'}
        </button>
      </div>

      {error && (
        <section className="panel">
          <h3>Unable to load database information</h3>
          <p className="muted">{error}</p>
        </section>
      )}

      {loading && !databaseInfo && (
        <p className="muted">Loading database information...</p>
      )}

      {!loading && !error && (
        <>
          <section className="stats-grid">
            <article className="stat-card">
              <div className="stat-icon blue">
                <Database size={21} />
              </div>

              <p className="stat-label">Connected Databases</p>

              <h2>{connectedCount} / 4</h2>

              <p className="stat-note">
                Database connections
              </p>
            </article>

            <article className="stat-card">
              <div className="stat-icon purple">
                <HardDrive size={21} />
              </div>

              <p className="stat-label">Total Tables</p>

              <h2>{tableCount}</h2>

              <p className="stat-note">
                Across configured databases
              </p>
            </article>

            <article className="stat-card">
              <div className="stat-icon green">
                <Users size={21} />
              </div>

              <p className="stat-label">Patient Records</p>

              <h2>{patientCount.toLocaleString()}</h2>

              <p className="stat-note">
                Patient health data records
              </p>
            </article>
          </section>

          {databaseHealth && (
            <section className="panel">
              <div className="panel-heading">
                <div>
                  <h3>Database Health</h3>

                  <p className="muted">
                    Health status reported by backend
                  </p>
                </div>

                <Activity size={21} />
              </div>

              <pre className="database-health">
                {JSON.stringify(databaseHealth, null, 2)}
              </pre>
            </section>
          )}

          {databases.length === 0 && (
            <section className="panel">
              <p className="muted">
                No database information available.
              </p>
            </section>
          )}

          {databases.map((database, index) => {
            const tables = Array.isArray(database.tables)
              ? database.tables
              : []

            return (
              <section
                className="panel"
                key={database.name || database.database_name || index}
              >
                <div className="panel-heading">
                  <div>
                    <h3>
                      {database.name ||
                        database.database_name ||
                        `Database ${index + 1}`}
                    </h3>

                    <p className="muted">
                      Status:{' '}
                      <strong>
                        {database.status || 'Not available'}
                      </strong>
                      {' · '}
                      Tables:{' '}
                      {database.table_count ?? tables.length}
                    </p>
                  </div>

                  <Database size={21} />
                </div>

                {tables.length > 0 ? (
                  <div className="table-container">
                    <table>
                      <thead>
                        <tr>
                          <th>Table Name</th>
                          <th>Record Count</th>
                        </tr>
                      </thead>

                      <tbody>
                        {tables.map((table, tableIndex) => (
                          <tr
                            key={table.name || tableIndex}
                          >
                            <td>{table.name}</td>

                            <td>
                              {typeof table.row_count === 'number'
                                ? table.row_count.toLocaleString()
                                : 'N/A'}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <p className="muted">
                    No table information available.
                  </p>
                )}
              </section>
            )
          })}
        </>
      )}
    </div>
  )
}
