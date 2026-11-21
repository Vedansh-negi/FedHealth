
import { useCallback, useEffect, useState } from 'react'
import {
  Activity,
  Cpu,
  HardDrive,
  MemoryStick,
  RefreshCw,
} from 'lucide-react'

import { getOSMetrics } from '../services/api'

export default function OSMonitoring() {
  const [resources, setResources] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadResources = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      const data = await getOSMetrics()

      if (!data) {
        throw new Error('Metrics load nahi hue')
      }

      setResources(data.resources ?? data)
    } catch (err) {
      setError(
        err.message || 'OS monitoring data load nahi hua'
      )
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadResources()
  }, [loadResources])

  const formatValue = (value, suffix = '') => {
    return typeof value === 'number'
      ? `${value.toFixed(1)}${suffix}`
      : 'N/A'
  }

  const metrics = resources
    ? [
        {
          label: 'CPU Usage',
          value: formatValue(resources.cpu_percent, '%'),
          icon: Cpu,
          color: 'blue',
        },
        {
          label: 'System RAM Usage',
          value: formatValue(resources.memory_percent, '%'),
          icon: MemoryStick,
          color: 'purple',
        },
        {
          label: 'System RAM Used',
          value: formatValue(
            resources.system_memory_used_mb,
            ' MB'
          ),
          icon: HardDrive,
          color: 'green',
        },
        {
          label: 'FedHealth Process RAM',
          value: formatValue(
            resources.process_memory_mb,
            ' MB'
          ),
          icon: Activity,
          color: 'orange',
        },
        {
          label: 'Available RAM',
          value: formatValue(
            resources.available_memory_mb,
            ' MB'
          ),
          icon: MemoryStick,
          color: 'blue',
        },
      ]
    : []

  return (
    <div className="dashboard-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">SYSTEM RESOURCES</p>

          <h1>OS Monitoring</h1>

          <p className="muted">
            Monitor system resources used while FedHealth is running.
          </p>
        </div>

        <button
          type="button"
          className="primary-button"
          onClick={loadResources}
          disabled={loading}
        >
          <RefreshCw size={17} />
          {loading ? 'Loading...' : 'Refresh Metrics'}
        </button>
      </div>

      {error && (
        <section className="panel">
          <h3>Unable to load system metrics</h3>
          <p className="muted">{error}</p>
        </section>
      )}

      {loading && !resources && (
        <p className="muted">Loading system metrics...</p>
      )}

      {resources && (
        <>
          <section className="stats-grid">
            {metrics.map(
              ({ label, value, icon: Icon, color }) => (
                <article className="stat-card" key={label}>
                  <div className={`stat-icon ${color}`}>
                    <Icon size={21} />
                  </div>

                  <p className="stat-label">{label}</p>

                  <h2>{value}</h2>

                  <p className="stat-note">
                    Latest system snapshot
                  </p>
                </article>
              )
            )}
          </section>

          <section className="panel">
            <div className="panel-heading">
              <div>
                <h3>Resource Monitoring</h3>

                <p className="muted">
                  Current resource usage of this machine
                </p>
              </div>

              <Activity size={21} />
            </div>

            <p className="data-note">
              Values reflect the latest snapshot collected from
              this machine. Refresh to collect a new snapshot.
            </p>
          </section>
        </>
      )}
    </div>
  )
}
