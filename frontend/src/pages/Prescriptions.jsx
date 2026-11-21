import { useEffect, useState } from 'react'

import {
  getPrescriptions,
  createPrescription,
  updatePrescription,
  deletePrescription,
  getPatients,
  getDoctors
} from '../services/api'

const HOSPITAL_ID = 1

const emptyForm = {
  record_id: '',
  patient_id: '',
  doctor_id: '',
  medicine_name: '',
  dosage: '',
  frequency: '',
  duration: '',
  instructions: ''
}

function Prescriptions() {
  const [prescriptions, setPrescriptions] = useState([])
  const [patients, setPatients] = useState([])
  const [doctors, setDoctors] = useState([])

  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)

  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  // Fetch all data
  const loadData = async () => {
    try {
      setLoading(true)
      setError('')

      const [
        prescriptionResponse,
        patientResponse,
        doctorResponse
      ] = await Promise.all([
        getPrescriptions(HOSPITAL_ID),
        getPatients(HOSPITAL_ID),
        getDoctors(HOSPITAL_ID)
      ])

      setPrescriptions(
        prescriptionResponse.prescriptions || []
      )

      setPatients(
        patientResponse.patients || []
      )

      setDoctors(
        doctorResponse.doctors || []
      )
    } catch (err) {
      setError(err.message || 'Failed to load prescriptions')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  // Form input handler
  const handleChange = (e) => {
    const { name, value } = e.target

    setForm((prev) => ({
      ...prev,
      [name]: value
    }))
  }

  // Reset form
  const resetForm = () => {
    setForm(emptyForm)
    setEditingId(null)
  }

  // Add / Update prescription
  const handleSubmit = async (e) => {
    e.preventDefault()

    try {
      setSaving(true)
      setError('')

      const payload = {
        record_id: Number(form.record_id),
        patient_id: Number(form.patient_id),
        doctor_id: Number(form.doctor_id),
        medicine_name: form.medicine_name.trim(),
        dosage: form.dosage.trim(),
        frequency: form.frequency.trim(),
        duration: form.duration.trim(),
        instructions: form.instructions.trim()
      }

      if (editingId) {
        await updatePrescription(
          editingId,
          payload,
          HOSPITAL_ID
        )
      } else {
        await createPrescription(
          payload,
          HOSPITAL_ID
        )
      }

      resetForm()
      await loadData()
    } catch (err) {
      setError(err.message || 'Failed to save prescription')
    } finally {
      setSaving(false)
    }
  }

  // Edit prescription
  const handleEdit = (prescription) => {
    setEditingId(prescription.prescription_id)

    setForm({
      record_id: prescription.record_id || '',
      patient_id: prescription.patient_id || '',
      doctor_id: prescription.doctor_id || '',
      medicine_name: prescription.medicine_name || '',
      dosage: prescription.dosage || '',
      frequency: prescription.frequency || '',
      duration: prescription.duration || '',
      instructions: prescription.instructions || ''
    })

    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    })
  }

  // Delete prescription
  const handleDelete = async (prescriptionId) => {
    const confirmDelete = window.confirm(
      'Are you sure you want to delete this prescription?'
    )

    if (!confirmDelete) return

    try {
      setError('')

      await deletePrescription(
        prescriptionId,
        HOSPITAL_ID
      )

      await loadData()
    } catch (err) {
      setError(err.message || 'Failed to delete prescription')
    }
  }

  // Search prescriptions
  const filteredPrescriptions = prescriptions.filter(
    (prescription) => {
      const searchText = search.toLowerCase()

      return (
        prescription.patient_name
          ?.toLowerCase()
          .includes(searchText) ||
        prescription.doctor_name
          ?.toLowerCase()
          .includes(searchText) ||
        prescription.medicine_name
          ?.toLowerCase()
          .includes(searchText)
      )
    }
  )

  return (
    <div className="prescriptions-page">

      {/* Header */}
      <div className="prescriptions-header">
        <div>
          <h1>Prescriptions</h1>
          <p>
            Manage patient prescriptions and medications
          </p>
        </div>

        <div className="prescriptions-count">
          <span>{prescriptions.length}</span>
          <small>Total Prescriptions</small>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="prescription-error">
          {error}
        </div>
      )}

      {/* Prescription Form */}
      <div className="prescription-form-card">

        <div className="prescription-form-heading">
          <h2>
            {editingId
              ? 'Edit Prescription'
              : 'Add New Prescription'}
          </h2>

          {editingId && (
            <button
              type="button"
              className="prescription-cancel-btn"
              onClick={resetForm}
            >
              Cancel Edit
            </button>
          )}
        </div>

        <form onSubmit={handleSubmit}>

          <div className="prescription-form-grid">

            {/* Patient */}
            <div className="prescription-field">
              <label>Patient *</label>

              <select
                name="patient_id"
                value={form.patient_id}
                onChange={handleChange}
                required
              >
                <option value="">
                  Select Patient
                </option>

                {patients.map((patient) => (
                  <option
                    key={patient.patient_id}
                    value={patient.patient_id}
                  >
                    {patient.patient_name ||
                      patient.full_name ||
                      `Patient ${patient.patient_id}`}
                  </option>
                ))}
              </select>
            </div>

            {/* Doctor */}
            <div className="prescription-field">
              <label>Doctor *</label>

              <select
                name="doctor_id"
                value={form.doctor_id}
                onChange={handleChange}
                required
              >
                <option value="">
                  Select Doctor
                </option>

                {doctors.map((doctor) => (
                  <option
                    key={doctor.doctor_id}
                    value={doctor.doctor_id}
                  >
                    {doctor.doctor_name ||
                      doctor.full_name ||
                      `Doctor ${doctor.doctor_id}`}
                  </option>
                ))}
              </select>
            </div>

            {/* Medical Record */}
            <div className="prescription-field">
              <label>Medical Record ID *</label>

              <input
                type="number"
                name="record_id"
                value={form.record_id}
                onChange={handleChange}
                placeholder="Enter medical record ID"
                min="1"
                required
              />
            </div>

            {/* Medicine */}
            <div className="prescription-field">
              <label>Medicine Name *</label>

              <input
                type="text"
                name="medicine_name"
                value={form.medicine_name}
                onChange={handleChange}
                placeholder="e.g. Paracetamol"
                required
              />
            </div>

            {/* Dosage */}
            <div className="prescription-field">
              <label>Dosage *</label>

              <input
                type="text"
                name="dosage"
                value={form.dosage}
                onChange={handleChange}
                placeholder="e.g. 500 mg"
                required
              />
            </div>

            {/* Frequency */}
            <div className="prescription-field">
              <label>Frequency *</label>

              <input
                type="text"
                name="frequency"
                value={form.frequency}
                onChange={handleChange}
                placeholder="e.g. Twice a day"
                required
              />
            </div>

            {/* Duration */}
            <div className="prescription-field">
              <label>Duration *</label>

              <input
                type="text"
                name="duration"
                value={form.duration}
                onChange={handleChange}
                placeholder="e.g. 5 days"
                required
              />
            </div>

            {/* Instructions */}
            <div className="prescription-field prescription-field-full">
              <label>Instructions</label>

              <textarea
                name="instructions"
                value={form.instructions}
                onChange={handleChange}
                placeholder="Enter medicine instructions..."
                rows="3"
              />
            </div>

          </div>

          <div className="prescription-form-actions">
            <button
              type="submit"
              className="prescription-submit-btn"
              disabled={saving}
            >
              {saving
                ? 'Saving...'
                : editingId
                  ? 'Update Prescription'
                  : 'Add Prescription'}
            </button>

            <button
              type="button"
              className="prescription-reset-btn"
              onClick={resetForm}
            >
              Reset
            </button>
          </div>

        </form>
      </div>

      {/* Prescription List */}
      <div className="prescription-list-card">

        <div className="prescription-list-heading">
          <div>
            <h2>All Prescriptions</h2>
            <p>
              View and manage prescribed medicines
            </p>
          </div>

          <input
            type="text"
            className="prescription-search"
            placeholder="Search patient or medicine..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>

        {loading ? (
          <div className="prescription-empty">
            Loading prescriptions...
          </div>
        ) : filteredPrescriptions.length === 0 ? (
          <div className="prescription-empty">
            No prescriptions found.
          </div>
        ) : (
          <div className="prescription-table-wrapper">

            <table className="prescription-table">

              <thead>
                <tr>
                  <th>ID</th>
                  <th>Patient</th>
                  <th>Doctor</th>
                  <th>Medicine</th>
                  <th>Dosage</th>
                  <th>Frequency</th>
                  <th>Duration</th>
                  <th>Prescribed At</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {filteredPrescriptions.map((prescription) => (
                  <tr key={prescription.prescription_id}>

                    <td>
                      #{prescription.prescription_id}
                    </td>

                    <td>
                      <strong>
                        {prescription.patient_name}
                      </strong>
                    </td>

                    <td>
                      {prescription.doctor_name}
                    </td>

                    <td>
                      <span className="medicine-name">
                        {prescription.medicine_name}
                      </span>
                    </td>

                    <td>
                      {prescription.dosage}
                    </td>

                    <td>
                      {prescription.frequency}
                    </td>

                    <td>
                      {prescription.duration}
                    </td>

                    <td>
                      {prescription.prescribed_at
                        ? new Date(
                            prescription.prescribed_at
                          ).toLocaleDateString()
                        : '-'}
                    </td>

                    <td>
                      <div className="prescription-actions">

                        <button
                          type="button"
                          className="prescription-edit-btn"
                          onClick={() => handleEdit(prescription)}
                        >
                          Edit
                        </button>

                        <button
                          type="button"
                          className="prescription-delete-btn"
                          onClick={() =>
                            handleDelete(
                              prescription.prescription_id
                            )
                          }
                        >
                          Delete
                        </button>

                      </div>
                    </td>

                  </tr>
                ))}
              </tbody>

            </table>

          </div>
        )}

      </div>

    </div>
  )
}

export default Prescriptions