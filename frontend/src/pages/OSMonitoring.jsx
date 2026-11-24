
import { useCallback, useEffect, useState } from 'react'
import {
  Activity,
  Cpu,
  HardDrive,
  MemoryStick,
  RefreshCw,
  Clock,
  Server,
} from 'lucide-react'

import { getOSMetrics, getOSProcesses } from '../services/api'

export default function OSMonitoring() {
  const [resources, setResources] = useState(null)
  const [processes, setProcesses] = useState([])
  const [loading, setLoading] = useState(true)
  const [processLoading, setProcessLoading] = useState(true)
  const [error, setError] = useState('')
  const [processError, setProcessError] = useState('')

  const loadData = useCallback(async () => {
    setLoading(true)
    setProcessLoading(true)
    setError('')
    setProcessError('')

    const [resourceResult, processResult] = await Promise.allSettled([
      getOSMetrics(),
      getOSProcesses(50),
    ])

    if (resourceResult.status === 'fulfilled') {
      const data = resourceResult.value

      if (data) {
        setResources(data.resources ?? data)
      } else {
        setError('Unable to load system metrics')
      }
    } else {
      setError(
        resourceResult.reason?.message || 'Unable to load system metrics'
      )
    }

    if (processResult.status === 'fulfilled') {
      setProcesses(processResult.value.processes ?? [])
    } else {
      setProcessError(
        processResult.reason?.message || 'Unable to load process history'
      )
    }

    setLoading(false)
    setProcessLoading(false)
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const formatValue = (value, suffix = '') =>
    typeof value === 'number' ? `${value.toFixed(1)}${suffix}` : 'N/A'

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
          value: formatValue(resources.system_memory_used_mb, ' MB'),
          icon: HardDrive,
          color: 'green',
        },
        {
          label: 'FedHealth Process RAM',
          value: formatValue(resources.process_memory_mb, ' MB'),
          icon: Activity,
          color: 'orange',
        },
        {
          label: 'Available RAM',
          value: formatValue(resources.available_memory_mb, ' MB'),
          icon: MemoryStick,
          color: 'blue',
        },
      ]
    : []

  const completedJobs = processes.filter(
    (process) => process.status === 'COMPLETED'
  ).length

  const miniBatchJobs = processes.filter(
    (process) => process.scheduling_unit === 'mini_batches'
  ).length

  return (
    <div className="dashboard-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">SYSTEM RESOURCES</p>
          <h1>OS Monitoring</h1>
          <p className="muted">
            Monitor system resources and federated training process scheduling.
          </p>
        </div>

        <button
          type="button"
          className="primary-button"
          onClick={loadData}
          disabled={loading || processLoading}
        >
          <RefreshCw size={17} />
          {loading || processLoading ? 'Loading...' : 'Refresh'}
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
            {metrics.map(({ label, value, icon: Icon, color }) => (
              <article className="stat-card" key={label}>
                <div className={`stat-icon ${color}`}>
                  <Icon size={21} />
                </div>
                <p className="stat-label">{label}</p>
                <h2>{value}</h2>
                <p className="stat-note">Latest system snapshot</p>
              </article>
            ))}
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
              Values reflect the latest snapshot collected from this machine.
              Refresh to collect a new snapshot.
            </p>
          </section>
        </>
      )}

      <section className="panel">
        <div className="panel-heading">
          <div>
            <h3>Round Robin Training Jobs</h3>
            <p className="muted">
              Federated hospital training process scheduling history
            </p>
          </div>
          <Server size={21} />
        </div>

        {processError && (
          <p className="muted">{processError}</p>
        )}

        {processLoading && (
          <p className="muted">Loading process history...</p>
        )}

        {!processLoading && !processError && processes.length === 0 && (
          <p className="muted">No process records found.</p>
        )}

        {!processLoading && processes.length > 0 && (
          <>
            <div className="stats-grid">
              <article className="stat-card">
                <div className="stat-icon blue">
                  <Server size={21} />
                </div>
                <p className="stat-label">Total Processes</p>
                <h2>{processes.length}</h2>
              </article>

              <article className="stat-card">
                <div className="stat-icon green">
                  <Activity size={21} />
                </div>
                <p className="stat-label">Completed</p>
                <h2>{completedJobs}</h2>
              </article>

              <article className="stat-card">
                <div className="stat-icon purple">
                  <Clock size={21} />
                </div>
                <p className="stat-label">Mini-batch Jobs</p>
                <h2>{miniBatchJobs}</h2>
              </article>
            </div>

            <div style={{ overflowX: 'auto', marginTop: '20px' }}>
              <table
                style={{
                  width: '100%',
                  borderCollapse: 'collapse',
                  textAlign: 'left',
                }}
              >
                <thead>
                  <tr>
                    {[
                      'Hospital',
                      'Process',
                      'Algorithm',
                      'Unit',
                      'Burst',
                      'Waiting',
                      'Turnaround',
                      'Response',
                      'Quantum',
                      'Status',
                    ].map((heading) => (
                      <th
                        key={heading}
                        style={{
                          padding: '12px',
                          borderBottom: '1px solid var(--border-color, #ddd)',
                          whiteSpace: 'nowrap',
                        }}
                      >
                        {heading}
                      </th>
                    ))}
                  </tr>
                </thead>

                <tbody>
                  {processes.map((process) => (
                    <tr key={process.process_log_id}>
                      <td style={{ padding: '12px' }}>
                        Hospital {process.hospital_id}
                      </td>
                      <td style={{ padding: '12px' }}>
                        {process.process_name}
                      </td>
                      <td style={{ padding: '12px' }}>
                        {process.scheduling_algorithm}
                      </td>
                      <td style={{ padding: '12px' }}>
                        {process.scheduling_unit ?? 'seconds'}
                      </td>
                      <td style={{ padding: '12px' }}>
                        {formatValue(process.burst_time_units)}
                      </td>
                      <td style={{ padding: '12px' }}>
                        {formatValue(process.waiting_time_units)}
                      </td>
                      <td style={{ padding: '12px' }}>
                        {formatValue(process.turnaround_time_units)}
                      </td>
                      <td style={{ padding: '12px' }}>
                        {formatValue(process.response_time_units)}
                      </td>
                      <td style={{ padding: '12px' }}>
                        {formatValue(process.time_quantum_units)}
                      </td>
                      <td style={{ padding: '12px' }}>
                        {process.status}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
    </div>
  )
}

