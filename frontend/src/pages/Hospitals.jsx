
import { useEffect, useState } from 'react'
import { Building2, RefreshCw, Users, Database } from 'lucide-react'

const API_URL = 'http://127.0.0.1:8000/api/hospitals'

function Hospitals() {
  const [hospitals, setHospitals] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  async function loadHospitals() {
    setLoading(true)
    setError('')

    try {
      const response = await fetch(API_URL)

      if (!response.ok) {
        throw new Error('Hospitals data load nahi ho paya.')
      }

      const data = await response.json()
      setHospitals(data.hospitals || [])
    } catch {
      setError('Backend se connection nahi ho paya. Backend server check karo.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadHospitals()
  }, [])

  const connectedCount = hospitals.filter(
    (hospital) => hospital.status === 'Connected'
  ).length

  const totalPatients = hospitals.reduce(
    (total, hospital) => total + (hospital.patient_count ?? 0),
    0
  )

  return (
    <section className="panel">
      <div className="panel-heading">
        <div>
          <h1>Hospitals</h1>
          <p className="muted">
            Participating hospitals in the FedHealth prototype
          </p>
        </div>

        <button
          className="icon-button"
          onClick={loadHospitals}
          disabled={loading}
          aria-label="Refresh hospitals"
        >
          <RefreshCw size={18} />
        </button>
      </div>

      {loading && <p className="muted">Loading hospitals...</p>}

      {error && (
        <div>
          <p>{error}</p>
          <button onClick={loadHospitals}>Try again</button>
        </div>
      )}

      {!loading && !error && (
        <>
          <div className="hospital-list">
            <div className="hospital-row">
              <div className="hospital-avatar">
                <Building2 size={19} />
              </div>
              <div className="hospital-info">
                <strong>Total hospitals</strong>
                <span>Registered demo hospitals</span>
              </div>
              <strong>{hospitals.length}</strong>
            </div>

            <div className="hospital-row">
              <div className="hospital-avatar">
                <Database size={19} />
              </div>
              <div className="hospital-info">
                <strong>Database connections</strong>
                <span>Successfully connected hospitals</span>
              </div>
              <strong>{connectedCount}/{hospitals.length}</strong>
            </div>

            <div className="hospital-row">
              <div className="hospital-avatar">
                <Users size={19} />
              </div>
              <div className="hospital-info">
                <strong>Total patient records</strong>
                <span>Records stored across hospital databases</span>
              </div>
              <strong>{totalPatients.toLocaleString()}</strong>
            </div>
          </div>

          <h2>Hospital Details</h2>

          <div className="hospital-list">
            {hospitals.map((hospital) => (
              <div className="hospital-row" key={hospital.id}>
                <div className="hospital-avatar">
                  <Building2 size={19} />
                </div>

                <div className="hospital-info">
                  <strong>{hospital.name}</strong>
                  <span>ID: {hospital.id}</span>
                  <span>
                    Patient records:{' '}
                    {hospital.patient_count == null
                      ? 'Unavailable'
                      : hospital.patient_count.toLocaleString()}
                  </span>
                  <span>{hospital.data_type || 'Dataset type unavailable'}</span>
                </div>

                <span className="status-badge">{hospital.status}</span>
              </div>
            ))}
          </div>

          <p className="data-note">
            Data is loaded from PostgreSQL through the FedHealth API.
            Hospital records use a public diabetes dataset for simulation,
            not real hospital patient data.
          </p>
        </>
      )}
    </section>
  )
}

export default Hospitals
