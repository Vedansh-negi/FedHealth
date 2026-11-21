
import { useEffect, useState } from 'react'
import {
  Search,
  Plus,
  Pencil,
  Trash2,
  Users,
  X,
  UserRound,
} from 'lucide-react'

import {
  getPatients,
  createPatient,
  updatePatient,
  deletePatient,
} from '../services/api'

function Patients() {
  const [patients, setPatients] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')

  const [showForm, setShowForm] = useState(false)
  const [editingPatient, setEditingPatient] = useState(null)
  const [saving, setSaving] = useState(false)

  const initialForm = {
    patient_number: '',
    full_name: '',
    date_of_birth: '',
    gender: 'Male',
    phone: '',
    email: '',
    address: '',
    blood_group: '',
    emergency_contact_name: '',
    emergency_contact_phone: '',
  }

  const [form, setForm] = useState(initialForm)

  // Load patients from backend
  async function loadPatients() {
    try {
      setLoading(true)
      setError('')

      const data = await getPatients(1)

      setPatients(data.patients || [])
    } catch (err) {
      setError(err.message || 'Patients load nahi ho paye')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadPatients()
  }, [])

  // Open create form
  function handleAdd() {
    setEditingPatient(null)
    setForm(initialForm)
    setShowForm(true)
  }

  // Open edit form
  function handleEdit(patient) {
    setEditingPatient(patient)

    setForm({
      patient_number: patient.patient_number || '',
      full_name: patient.full_name || '',
      date_of_birth: patient.date_of_birth
        ? String(patient.date_of_birth).slice(0, 10)
        : '',
      gender: patient.gender || 'Male',
      phone: patient.phone || '',
      email: patient.email || '',
      address: patient.address || '',
      blood_group: patient.blood_group || '',
      emergency_contact_name:
        patient.emergency_contact_name || '',
      emergency_contact_phone:
        patient.emergency_contact_phone || '',
    })

    setShowForm(true)
  }

  // Form input handler
  function handleChange(event) {
    const { name, value } = event.target

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }))
  }

  // Create or update patient
  async function handleSubmit(event) {
    event.preventDefault()

    try {
      setSaving(true)
      setError('')

      const patientData = {
        ...form,
        phone: form.phone || null,
        email: form.email || null,
        address: form.address || null,
        blood_group: form.blood_group || null,
        emergency_contact_name:
          form.emergency_contact_name || null,
        emergency_contact_phone:
          form.emergency_contact_phone || null,
      }

      if (editingPatient) {
        await updatePatient(
          editingPatient.patient_id,
          patientData,
          1
        )
      } else {
        await createPatient(patientData, 1)
      }

      setShowForm(false)
      setEditingPatient(null)
      setForm(initialForm)

      await loadPatients()
    } catch (err) {
      setError(err.message || 'Patient save nahi ho paya')
    } finally {
      setSaving(false)
    }
  }

  // Delete patient
  async function handleDelete(patient) {
    const confirmed = window.confirm(
      `Are you sure you want to delete ${patient.full_name}?`
    )

    if (!confirmed) return

    try {
      setError('')

      await deletePatient(patient.patient_id, 1)

      await loadPatients()
    } catch (err) {
      setError(err.message || 'Patient delete nahi ho paya')
    }
  }

  // Search patients
  const filteredPatients = patients.filter((patient) => {
    const query = search.toLowerCase()

    return (
      String(patient.patient_number || '')
        .toLowerCase()
        .includes(query) ||
      String(patient.full_name || '')
        .toLowerCase()
        .includes(query) ||
      String(patient.phone || '')
        .toLowerCase()
        .includes(query)
    )
  })

  return (
    <div className="dashboard-page">
      {/* Page heading */}
      <div className="page-heading">
        <div>
          <p className="eyebrow">PATIENT MANAGEMENT</p>

          <h1>Patients</h1>

          <p className="muted">
            Manage registered patients and their information.
          </p>
        </div>

        <button className="patient-add-button" onClick={handleAdd}>
          <Plus size={18} />
          Add Patient
        </button>
      </div>

      {/* Summary card */}
      <section className="stats-grid patients-stats">
        <article className="stat-card">
          <div className="stat-icon blue">
            <Users size={21} />
          </div>

          <p className="stat-label">Total Patients</p>

          <h2>{patients.length}</h2>

          <p className="stat-note">Registered in Hospital 1</p>
        </article>
      </section>

      {/* Patients table */}
      <section className="panel">
        <div className="patients-toolbar">
          <div>
            <h3>Patient Records</h3>

            <p className="muted">
              Patient information from the backend database
            </p>
          </div>

          <label className="patients-search">
            <Search size={17} />

            <input
              type="text"
              placeholder="Search patients..."
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </label>
        </div>

        {error && (
          <div className="patients-error">
            {error}
          </div>
        )}

        {loading ? (
          <p className="muted">Loading patients...</p>
        ) : (
          <div className="patients-table-wrapper">
            <table className="patients-table">
              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Patient Number</th>
                  <th>Date of Birth</th>
                  <th>Gender</th>
                  <th>Phone</th>
                  <th>Blood Group</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {filteredPatients.map((patient) => (
                  <tr key={patient.patient_id}>
                    <td>
                      <div className="patient-name-cell">
                        <div className="patient-table-avatar">
                          <UserRound size={17} />
                        </div>

                        <strong>{patient.full_name}</strong>
                      </div>
                    </td>

                    <td>{patient.patient_number}</td>

                    <td>
                      {patient.date_of_birth
                        ? String(patient.date_of_birth).slice(0, 10)
                        : '-'}
                    </td>

                    <td>{patient.gender || '-'}</td>

                    <td>{patient.phone || '-'}</td>

                    <td>{patient.blood_group || '-'}</td>

                    <td>
                      <div className="patient-actions">
                        <button
                          className="patient-action edit"
                          title="Edit patient"
                          onClick={() => handleEdit(patient)}
                        >
                          <Pencil size={16} />
                        </button>

                        <button
                          className="patient-action delete"
                          title="Delete patient"
                          onClick={() => handleDelete(patient)}
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}

                {filteredPatients.length === 0 && (
                  <tr>
                    <td colSpan="7" className="patients-empty">
                      {search
                        ? 'No patients match your search.'
                        : 'No patients registered yet.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {/* Add / Edit modal */}
      {showForm && (
        <div className="patient-modal-overlay">
          <div className="patient-modal">
            <div className="patient-modal-header">
              <div>
                <h2>
                  {editingPatient
                    ? 'Edit Patient'
                    : 'Add New Patient'}
                </h2>

                <p className="muted">
                  Enter patient details below.
                </p>
              </div>

              <button
                className="patient-modal-close"
                onClick={() => setShowForm(false)}
                aria-label="Close"
              >
                <X size={20} />
              </button>
            </div>

            <form onSubmit={handleSubmit}>
              <div className="patient-form-grid">
                <label>
                  Patient Number *
                  <input
                    name="patient_number"
                    value={form.patient_number}
                    onChange={handleChange}
                    required
                    maxLength="50"
                  />
                </label>

                <label>
                  Full Name *
                  <input
                    name="full_name"
                    value={form.full_name}
                    onChange={handleChange}
                    required
                    maxLength="150"
                  />
                </label>

                <label>
                  Date of Birth *
                  <input
                    type="date"
                    name="date_of_birth"
                    value={form.date_of_birth}
                    onChange={handleChange}
                    required
                  />
                </label>

                <label>
                  Gender *
                  <select
                    name="gender"
                    value={form.gender}
                    onChange={handleChange}
                    required
                  >
                    <option value="Male">Male</option>
                    <option value="Female">Female</option>
                    <option value="Other">Other</option>
                  </select>
                </label>

                <label>
                  Phone
                  <input
                    name="phone"
                    value={form.phone}
                    onChange={handleChange}
                  />
                </label>

                <label>
                  Email
                  <input
                    type="email"
                    name="email"
                    value={form.email}
                    onChange={handleChange}
                  />
                </label>

                <label>
                  Blood Group
                  <select
                    name="blood_group"
                    value={form.blood_group}
                    onChange={handleChange}
                  >
                    <option value="">Select blood group</option>
                    <option value="A+">A+</option>
                    <option value="A-">A-</option>
                    <option value="B+">B+</option>
                    <option value="B-">B-</option>
                    <option value="AB+">AB+</option>
                    <option value="AB-">AB-</option>
                    <option value="O+">O+</option>
                    <option value="O-">O-</option>
                  </select>
                </label>

                <label>
                  Address
                  <input
                    name="address"
                    value={form.address}
                    onChange={handleChange}
                  />
                </label>

                <label>
                  Emergency Contact Name
                  <input
                    name="emergency_contact_name"
                    value={form.emergency_contact_name}
                    onChange={handleChange}
                  />
                </label>

                <label>
                  Emergency Contact Phone
                  <input
                    name="emergency_contact_phone"
                    value={form.emergency_contact_phone}
                    onChange={handleChange}
                  />
                </label>
              </div>

              <div className="patient-form-actions">
                <button
                  type="button"
                  className="patient-cancel-button"
                  onClick={() => setShowForm(false)}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="patient-submit-button"
                  disabled={saving}
                >
                  {saving
                    ? 'Saving...'
                    : editingPatient
                      ? 'Update Patient'
                      : 'Create Patient'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default Patients
