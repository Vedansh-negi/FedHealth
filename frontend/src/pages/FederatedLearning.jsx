
import { useCallback, useEffect, useState } from 'react'

import {
  Activity,
  Building2,
  Network,
  Play,
  Target,
  TrendingUp,
} from 'lucide-react'

import {
  getDashboardData,
  getFederatedSummary,
  getFederatedComparison,
  getHospitals,
  getSavedUser,
  runFederatedRound,
} from '../services/api'

const pct = (value) =>
  typeof value === 'number' ? `${(value * 100).toFixed(2)}%` : '—'

const formatTime = (value) =>
  value ? new Date(value).toLocaleString() : '—'

export default function FederatedLearning() {
  const user = getSavedUser()
  const canRunTraining = ['admin', 'doctor'].includes(user?.role)

  const [summary, setSummary] = useState(null)
  const [hospitals, setHospitals] = useState([])
  const [federated, setFederated] = useState(null)
  const [comparison, setComparison] = useState(null)

  const [error, setError] = useState('')
  const [federatedError, setFederatedError] = useState('')
  const [comparisonError, setComparisonError] = useState('')
  const [actionMessage, setActionMessage] = useState('')
  const [starting, setStarting] = useState(false)

  const load = useCallback(async () => {
    try {
      const [dashboardData, hospitalData] = await Promise.all([
        getDashboardData(),
        getHospitals(),
      ])

      setSummary(dashboardData)
      setHospitals(
        Array.isArray(hospitalData?.hospitals)
          ? hospitalData.hospitals
          : [],
      )
      setError('')
    } catch (err) {
      setError(err.message || 'Unable to load dashboard data')
    }

    try {
      setFederated(await getFederatedSummary(10))
      setFederatedError('')
    } catch (err) {
      setFederatedError(err.message || 'Unable to load training data')
    }

    try {
      setComparison(await getFederatedComparison())
      setComparisonError('')
    } catch (err) {
      setComparisonError(
        err.message || 'Unable to load comparison data',
      )
    }
  }, [])

  useEffect(() => {
    load()
  }, [load])

  // While a round is running, refresh every 5 seconds.
  const inProgress = federated?.training_in_progress

  useEffect(() => {
    if (!inProgress) return undefined

    const timer = setInterval(load, 5000)
    return () => clearInterval(timer)
  }, [inProgress, load])

  async function handleStartRound() {
    setStarting(true)
    setActionMessage('')

    try {
      const result = await runFederatedRound()
      setActionMessage(result?.message || 'Training started')
      await load()
    } catch (err) {
      setActionMessage(err.message || 'Unable to start training')
    } finally {
      setStarting(false)
    }
  }

  const dashboardHospitals = Array.isArray(summary?.hospitals)
    ? summary.hospitals
    : []

  const hospitalStats = new Map(
    dashboardHospitals.map((hospital) => [
      hospital.hospital_id,
      hospital,
    ]),
  )

  const totalPatients = dashboardHospitals.reduce(
    (total, hospital) =>
      total +
      (typeof hospital.patients === 'number' ? hospital.patients : 0),
    0,
  )

  const totalMLRecords = dashboardHospitals.reduce(
    (total, hospital) =>
      total +
      (typeof hospital.ml_dataset_records === 'number'
        ? hospital.ml_dataset_records
        : 0),
    0,
  )

  const latestModel = summary?.latest_model

  const rounds = Array.isArray(federated?.rounds)
    ? federated.rounds
    : []

  const updates = Array.isArray(federated?.latest_hospital_updates)
    ? federated.latest_hospital_updates
    : []

  const comparisonResults = Array.isArray(comparison?.results)
    ? comparison.results
    : []

  const stats = [
    {
      label: 'Federated Rounds',
      value:
        typeof summary?.federated_rounds === 'number'
          ? String(summary.federated_rounds)
          : '—',
      note: 'Completed training rounds',
      icon: Network,
      color: 'purple',
    },
    {
      label: 'Global Model Accuracy',
      value: pct(latestModel?.accuracy),
      note: latestModel?.evaluated
        ? latestModel.model_version
        : 'Not evaluated yet',
      icon: Target,
      color: 'green',
    },
    {
      label: 'Participating Hospitals',
      value: String(hospitals.length),
      note: 'Hospitals returned by backend',
      icon: Building2,
      color: 'blue',
    },
    {
      label: 'Training Status',
      value: inProgress ? 'Running' : 'Idle',
      note: inProgress
        ? 'A federated round is in progress'
        : 'Ready for the next round',
      icon: Activity,
      color: 'orange',
    },
  ]

  if (error) {
    return (
      <div className="dashboard-page">
        <div className="page-heading">
          <div>
            <p className="eyebrow">FEDERATED LEARNING</p>
            <h1>Federated Learning</h1>
          </div>
        </div>

        <section className="panel">
          <h3>Unable to load data</h3>
          <p className="muted">{error}</p>
        </section>
      </div>
    )
  }

  if (!summary) {
    return <p className="muted">Loading federated learning data...</p>
  }

  return (
    <div className="dashboard-page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">FEDERATED LEARNING</p>

          <h1>Federated Learning</h1>

          <p className="muted">
            Monitor federated training and participating hospitals.
          </p>
        </div>

        {canRunTraining ? (
          <button
            type="button"
            className="primary-button"
            onClick={handleStartRound}
            disabled={starting || inProgress}
          >
            <Play size={17} />
            {inProgress
              ? 'Training in progress...'
              : starting
                ? 'Starting...'
                : 'Run Training Round'}
          </button>
        ) : (
          <span className="date-chip">FedHealth Prototype</span>
        )}
      </div>

      {actionMessage && (
        <p className="data-note">{actionMessage}</p>
      )}

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

      {/* Participating Hospitals */}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h3>Participating Hospitals</h3>

            <p className="muted">
              Hospital information retrieved from the backend API
            </p>
          </div>

          <Building2 size={21} />
        </div>

        {hospitals.length === 0 && (
          <p className="muted">No hospital records available.</p>
        )}

        <div className="hospital-list">
          {hospitals.map((hospital) => {
            const stat = hospitalStats.get(hospital.hospital_id)

            const patients =
              typeof stat?.patients === 'number'
                ? stat.patients
                : 'N/A'

            const doctors =
              typeof stat?.doctors === 'number'
                ? stat.doctors
                : 'N/A'

            const appointments =
              typeof stat?.appointments === 'number'
                ? stat.appointments
                : 'N/A'

            const mlRecords =
              typeof stat?.ml_dataset_records === 'number'
                ? stat.ml_dataset_records
                : 'N/A'

            return (
              <div
                className="hospital-row"
                key={hospital.hospital_id}
              >
                <div className="hospital-avatar">
                  <Building2 size={19} />
                </div>

                <div className="hospital-info">
                  <strong>{hospital.hospital_name}</strong>

                  <span>{hospital.database_name}</span>

                  <span>
                    {patients} patients · {doctors} doctors ·{' '}
                    {appointments} appointments
                  </span>

                  <span>
                    {typeof mlRecords === 'number'
                      ? mlRecords.toLocaleString()
                      : mlRecords}{' '}
                    ML dataset records
                  </span>
                </div>

                <span className="status-badge">
                  {hospital.status === 'connected'
                    ? 'Connected'
                    : 'Unreachable'}
                </span>
              </div>
            )
          })}
        </div>

        <p className="data-note">
          Registered patients: {totalPatients.toLocaleString()} ·
          Total ML dataset records: {totalMLRecords.toLocaleString()}.
          Raw patient data stays in each hospital database; only model
          parameters are shared with the aggregator.
        </p>
      </section>

      {/* Global Model Performance */}
      <section className="panel performance-panel">
        <div className="panel-heading">
          <div>
            <h3>Global Model Performance</h3>

            <p className="muted">
              {latestModel
                ? `${latestModel.model_version} (validation split)`
                : 'No global model trained yet'}
            </p>
          </div>

          <TrendingUp size={21} />
        </div>

        {latestModel?.evaluated ? (
          [
            ['Accuracy', latestModel.accuracy],
            ['Precision', latestModel.precision],
            ['Recall', latestModel.recall],
            ['F1 Score', latestModel.f1_score],
          ].map(([label, value]) => (
            <div className="metric-row" key={label}>
              <div className="metric-label">
                <span>{label}</span>
                <strong>{pct(value)}</strong>
              </div>

              <div className="progress-track">
                <div
                  className="progress-fill"
                  style={{
                    width: `${Math.min((value || 0) * 100, 100)}%`,
                  }}
                />
              </div>
            </div>
          ))
        ) : (
          <p className="muted">
            Metrics appear after a round has been trained and evaluated.
          </p>
        )}

        <p className="data-note">
          These are validation-split results on simulated hospital
          data. They are not an independent test and do not show
          clinical usefulness.
        </p>
      </section>

      {/* Centralized vs Federated Comparison */}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h3>Centralized vs Federated Learning</h3>

            <p className="muted">
              Comparison of models evaluated on the same held-out test
              dataset
            </p>
          </div>

          <TrendingUp size={21} />
        </div>

        {comparisonError && (
          <p className="muted">{comparisonError}</p>
        )}

        {!comparisonError && !comparison && (
          <p className="muted">
            Loading comparison results...
          </p>
        )}

        {!comparisonError &&
          comparison &&
          comparisonResults.length === 0 && (
            <p className="muted">
              No comparison results available. Run the centralized
              training pipeline first.
            </p>
          )}

        {!comparisonError && comparisonResults.length > 0 && (
          <>
            <p className="data-note">
              Comparison run: {comparison.comparison_run || '—'}
            </p>

            <div className="patients-table-wrapper">
              <table className="patients-table">
                <thead>
                  <tr>
                    <th>Model</th>
                    <th>Accuracy</th>
                    <th>Precision</th>
                    <th>Recall</th>
                    <th>F1 Score</th>
                    <th>ROC-AUC</th>
                    <th>Evaluation Set</th>
                  </tr>
                </thead>

                <tbody>
                  {comparisonResults.map((model, index) => (
                    <tr
                      key={`${model.model_name}-${index}`}
                    >
                      <td>
                        <strong>{model.model_name}</strong>
                      </td>

                      <td>{pct(model.accuracy)}</td>
                      <td>{pct(model.precision)}</td>
                      <td>{pct(model.recall)}</td>
                      <td>{pct(model.f1_score)}</td>

                      <td>
                        {typeof model.roc_auc === 'number'
                          ? model.roc_auc.toFixed(4)
                          : '—'}
                      </td>

                      <td>{model.evaluation_set || '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="data-note">
              All models were evaluated using the same held-out test
              dataset. Centralized training uses pooled training data,
              whereas federated training keeps raw training data at
              individual hospitals and aggregates model updates.
            </p>

            <p className="data-note">
              Technical note: The centralized model uses scikit-learn
              Logistic Regression with LBFGS optimization, while the
              federated model uses custom mini-batch gradient descent.
              The optimization methods differ. Inter-hospital
              communication in this prototype is simulated; this
              comparison is not clinical validation.
            </p>
          </>
        )}
      </section>

      {/* Training Rounds */}
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h3>Training Rounds</h3>

            <p className="muted">Most recent federated rounds</p>
          </div>

          <Network size={21} />
        </div>

        {federatedError && (
          <p className="muted">{federatedError}</p>
        )}

        {!federatedError && rounds.length === 0 && (
          <p className="muted">No training rounds recorded yet.</p>
        )}

        {rounds.length > 0 && (
          <div className="patients-table-wrapper">
            <table className="patients-table">
              <thead>
                <tr>
                  <th>Round</th>
                  <th>Status</th>
                  <th>Model version</th>
                  <th>Accuracy</th>
                  <th>F1</th>
                  <th>Started</th>
                  <th>Finished</th>
                </tr>
              </thead>

              <tbody>
                {rounds.map((round) => (
                  <tr key={round.round_id}>
                    <td>#{round.round_number}</td>
                    <td>{round.status}</td>
                    <td>{round.global_model_version || '—'}</td>
                    <td>{pct(round.accuracy)}</td>
                    <td>{pct(round.f1_score)}</td>
                    <td>{formatTime(round.start_time)}</td>
                    <td>{formatTime(round.end_time)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Latest Hospital Updates */}
      {updates.length > 0 && (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h3>Latest Hospital Updates</h3>

              <p className="muted">
                Local training results from the most recent round
              </p>
            </div>

            <Building2 size={21} />
          </div>

          <div className="patients-table-wrapper">
            <table className="patients-table">
              <thead>
                <tr>
                  <th>Hospital</th>
                  <th>Samples</th>
                  <th>Accuracy</th>
                  <th>Precision</th>
                  <th>Recall</th>
                  <th>F1</th>
                  <th>Training time</th>
                </tr>
              </thead>

              <tbody>
                {updates.map((update) => (
                  <tr key={update.hospital_id}>
                    <td>Hospital {update.hospital_id}</td>

                    <td>
                      {update.sample_count?.toLocaleString()}
                    </td>

                    <td>{pct(update.accuracy)}</td>
                    <td>{pct(update.precision)}</td>
                    <td>{pct(update.recall)}</td>
                    <td>{pct(update.f1_score)}</td>

                    <td>
                      {typeof update.training_time_seconds === 'number'
                        ? `${update.training_time_seconds.toFixed(1)} s`
                        : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  )
}

