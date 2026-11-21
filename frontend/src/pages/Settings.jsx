
import { useCallback, useEffect, useState } from 'react'
import {
  Server,
  Database,
  Brain,
  RefreshCw,
  Activity,
} from 'lucide-react'

import {
  getDatabaseHealth,
  getDashboardData,
} from '../services/api'

const API_BASE_URL = 'http://127.0.0.1:8000'

export default function Settings() {
  const [databaseHealth, setDatabaseHealth] = useState(null)
  const [summary, setSummary] = useState(null)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadSettings = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      const [healthData, dashboardData] = await Promise.all([
        getDatabaseHealth(),
        getDashboardData(),
      ])

      setDatabaseHealth(healthData)
      setSummary(dashboardData)
    } catch (err) {
      setError(
        err.message || 'Settings data load nahi hua'
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadSettings()
  }, [loadSettings])

  const databases = databaseHealth?.databases
    ? Object.entries(databaseHealth.databases)
    : []

  const connectedCount = databases.filter(
    ([, status]) =>
      status === 'connected' ||
      status === 'Connected'
  ).length

  return (
    <div className="dashboard-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">SYSTEM CONFIGURATION</p>

          <h1>Settings</h1>

          <p className="muted">
            View FedHealth API, database connections and model configuration.
          </p>
        </div>

        <button
          type="button"
          className="primary-button"
          onClick={loadSettings}
          disabled={loading}
        >
          <RefreshCw size={17} />
          {loading ? 'Checking...' : 'Refresh Status'}
        </button>
      </div>

      {error && (
        <section className="panel">
          <h3>Unable to load settings</h3>
          <p className="muted">{error}</p>
        </section>
      )}

      {loading && !databaseHealth && (
        <p className="muted">Loading settings...</p>
      )}

      <section className="stats-grid">
        <article className="stat-card">
          <div className="stat-icon blue">
            <Server size={21} />
          </div>

          <p className="stat-label">Backend API</p>

          <h2>
            {databaseHealth ? 'Online' : loading ? 'Checking...' : 'Offline'}
          </h2>

          <p className="stat-note">
            FastAPI backend status
          </p>
        </article>

        <article className="stat-card">
          <div className="stat-icon green">
            <Database size={21} />
          </div>

          <p className="stat-label">Connected Databases</p>

          <h2>
            {connectedCount} / {databases.length}
          </h2>

          <p className="stat-note">
            Database health status
          </p>
        </article>

        <article className="stat-card">
          <div className="stat-icon purple">
            <Brain size={21} />
          </div>

          <p className="stat-label">Federated Rounds</p>

          <h2>
            {summary?.federated_rounds ?? 'N/A'}
          </h2>

          <p className="stat-note">
            Completed training rounds
          </p>
        </article>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h3>Backend Configuration</h3>

            <p className="muted">
              Current backend connection details
            </p>
          </div>

          <Server size={21} />
        </div>

        <div className="settings-row">
          <span>API URL</span>
          <strong>{API_BASE_URL}</strong>
        </div>

        <div className="settings-row">
          <span>API Status</span>
          <strong>
            {databaseHealth
              ? 'Responding'
              : loading
                ? 'Checking...'
                : 'Unavailable'}
          </strong>
        </div>

        <div className="settings-row">
          <span>API Framework</span>
          <strong>FastAPI</strong>
        </div>
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h3>Database Connections</h3>

            <p className="muted">
              Current database connection status
            </p>
          </div>

          <Database size={21} />
        </div>

        {databaseHealth && (
          <>
            <div className="settings-row">
              <span>Overall Status</span>
              <strong>{databaseHealth.status}</strong>
            </div>

            <div className="settings-row">
              <span>Connected Databases</span>
              <strong>
                {connectedCount} / {databases.length}
              </strong>
            </div>

            {databases.map(([name, status]) => (
              <div className="settings-row" key={name}>
                <span>{name}</span>
                <strong>{status}</strong>
              </div>
            ))}
          </>
        )}

        {!databaseHealth && !loading && (
          <p className="muted">
            Database health information unavailable.
          </p>
        )}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h3>Model Configuration</h3>

            <p className="muted">
              Federated learning model information
            </p>
          </div>

          <Activity size={21} />
        </div>

        <div className="settings-row">
          <span>Model Type</span>
          <strong>Logistic Regression</strong>
        </div>

        <div className="settings-row">
          <span>Federated Algorithm</span>
          <strong>FedAvg</strong>
        </div>

        <div className="settings-row">
          <span>Model Version</span>
          <strong>
            {summary?.federated_rounds > 0
              ? 'Trained global model available'
              : 'No completed rounds'}
          </strong>
        </div>

        <div className="settings-row">
          <span>Completed Rounds</span>
          <strong>
            {summary?.federated_rounds ?? 'N/A'}
          </strong>
        </div>
      </section>

      <p className="data-note">
        This page displays the current configuration. It does not modify
        database credentials or model training settings.
      </p>
    </div>
  )
}
