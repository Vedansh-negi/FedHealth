
import { useCallback, useEffect, useState } from 'react'
import {
  Activity,
  Cpu,
  HardDrive,
  MemoryStick,
  RefreshCw,
} from 'lucide-react'

import { getOSMetrics, getOSProcesses } from '../services/api'

export default function OSMonitoring() {
  const [resources, setResources] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [processes, setProcesses] = useState([])
  const [processError, setProcessError] = useState('')

  const loadResources = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      const data = await getOSMetrics()

      if (!data) {
        throw new Error('Metrics load nahi hue')
      }

      setResources(data.resources ?? data)
      try {
        const processData = await getOSProcesses(50)
        setProcesses(processData.processes ?? [])
        setProcessError('')
      } catch (processErr) {
        setProcessError(processErr.message || 'Unable to load scheduler history')
      }
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

          <section className="panel">
            <div className="panel-heading">
              <div>
                <h3>Round Robin Training Jobs</h3>
                <p className="muted">
                  Hospital local-training tasks scheduled during federated rounds.
                </p>
              </div>
              <Cpu size={21} />
            </div>

            {processError && <p className="muted">{processError}</p>}

            {processes.length === 0 ? (
              <p className="data-note">
                No scheduled training jobs recorded yet. Start a federated round to populate this table.
              </p>
            ) : (
              <div className="patients-table-wrapper">
                <table className="patients-table">
                  <thead>
                    <tr>
                      <th>Hospital</th>
                      <th>Task</th>
                      <th>Algorithm</th>
                      <th>Burst</th>
                      <th>Waiting</th>
                      <th>Turnaround</th>
                      <th>Response</th>
                      <th>Unit</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {processes.map((process) => (
                      <tr key={process.process_log_id}>
                        <td>Hospital {process.hospital_id}</td>
                        <td>{process.process_name}</td>
                        <td>{process.scheduling_algorithm}</td>
                        <td>{process.burst_time_units ?? '—'}</td>
                        <td>{process.waiting_time_units ?? '—'}</td>
                        <td>{process.turnaround_time_units ?? '—'}</td>
                        <td>{process.response_time_units ?? '—'}</td>
                        <td>{process.scheduling_unit ?? 'seconds'}</td>
                        <td>{process.status}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
