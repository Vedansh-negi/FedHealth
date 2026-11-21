import { useEffect, useState } from "react"

import {
  getMedicalRecords,
  createMedicalRecord,
  updateMedicalRecord,
  deleteMedicalRecord,
  getPatients,
  getDoctors
} from "../services/api"

const HOSPITAL_ID = 1

const initialForm = {
  patient_id: "",
  doctor_id: "",
  appointment_id: "",
  diagnosis: "",
  clinical_notes: "",
  blood_pressure: "",
  heart_rate: "",
  temperature: "",
  oxygen_saturation: 100,
  height_cm: "",
  weight_kg: ""
}

export default function MedicalRecords() {
  const [records, setRecords] = useState([])
  const [patients, setPatients] = useState([])
  const [doctors, setDoctors] = useState([])

  const [form, setForm] = useState(initialForm)

  const [editingId, setEditingId] = useState(null)
  const [showForm, setShowForm] = useState(false)

  const [search, setSearch] = useState("")
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")

  useEffect(() => {
    loadData()
  }, [])

  // ================= LOAD DATA =================

  const loadData = async () => {
    try {
      setLoading(true)
      setError("")

      const [recordsData, patientsData, doctorsData] =
        await Promise.all([
          getMedicalRecords(HOSPITAL_ID),
          getPatients(HOSPITAL_ID),
          getDoctors(HOSPITAL_ID)
        ])

      setRecords(
        recordsData.medical_records || []
      )

      setPatients(
        patientsData.patients || []
      )

      setDoctors(
        doctorsData.doctors || []
      )
    } catch (err) {
      setError(err.message || "Failed to load medical records")
    } finally {
      setLoading(false)
    }
  }

  // ================= FORM HANDLING =================

  const handleChange = (e) => {
    const { name, value } = e.target

    setForm((prev) => ({
      ...prev,
      [name]: value
    }))
  }

  const resetForm = () => {
    setForm(initialForm)
    setEditingId(null)
    setShowForm(false)
  }

  const handleEdit = (record) => {
    setForm({
      patient_id: record.patient_id ?? "",
      doctor_id: record.doctor_id ?? "",
      appointment_id: record.appointment_id ?? "",
      diagnosis: record.diagnosis ?? "",
      clinical_notes: record.clinical_notes ?? "",
      blood_pressure: record.blood_pressure ?? "",
      heart_rate: record.heart_rate ?? "",
      temperature: record.temperature ?? "",
      oxygen_saturation: record.oxygen_saturation ?? 100,
      height_cm: record.height_cm ?? "",
      weight_kg: record.weight_kg ?? ""
    })

    setEditingId(record.record_id)
    setShowForm(true)

    window.scrollTo({
      top: 0,
      behavior: "smooth"
    })
  }

  // ================= SAVE RECORD =================

  const handleSubmit = async (e) => {
    e.preventDefault()

    try {
      setError("")
      setSuccess("")

      const payload = {
        patient_id: Number(form.patient_id),
        doctor_id: Number(form.doctor_id),

        appointment_id:
          form.appointment_id === ""
            ? null
            : Number(form.appointment_id),

        diagnosis: form.diagnosis,
        clinical_notes: form.clinical_notes,

        blood_pressure: form.blood_pressure,

        heart_rate:
          form.heart_rate === ""
            ? null
            : Number(form.heart_rate),

        temperature:
          form.temperature === ""
            ? null
            : Number(form.temperature),

        oxygen_saturation:
          Number(form.oxygen_saturation),

        height_cm:
          form.height_cm === ""
            ? null
            : Number(form.height_cm),

        weight_kg:
          form.weight_kg === ""
            ? null
            : Number(form.weight_kg)
      }

      if (editingId) {
        await updateMedicalRecord(
          editingId,
          payload,
          HOSPITAL_ID
        )

        setSuccess("Medical record updated successfully")
      } else {
        await createMedicalRecord(
          payload,
          HOSPITAL_ID
        )

        setSuccess("Medical record created successfully")
      }

      resetForm()
      await loadData()
    } catch (err) {
      setError(err.message || "Failed to save medical record")
    }
  }

  // ================= DELETE RECORD =================

  const handleDelete = async (recordId) => {
    const confirmed = window.confirm(
      "Are you sure you want to delete this medical record?"
    )

    if (!confirmed) return

    try {
      setError("")
      setSuccess("")

      await deleteMedicalRecord(
        recordId,
        HOSPITAL_ID
      )

      setSuccess("Medical record deleted successfully")

      await loadData()
    } catch (err) {
      setError(err.message || "Failed to delete medical record")
    }
  }

  // ================= SEARCH =================

  const filteredRecords = records.filter((record) => {
    const searchText = search.toLowerCase()

    return (
      String(record.record_id).includes(searchText) ||
      String(record.patient_name || "")
        .toLowerCase()
        .includes(searchText) ||
      String(record.doctor_name || "")
        .toLowerCase()
        .includes(searchText) ||
      String(record.diagnosis || "")
        .toLowerCase()
        .includes(searchText)
    )
  })

  // ================= UI =================

  return (
    <div className="medical-records-page">

      {/* HEADER */}

      <div className="medical-records-header">
        <div>
          <h1>Medical Records</h1>

          <p>
            Manage patient medical history and clinical records
          </p>
        </div>

        <button
          className="medical-primary-btn"
          onClick={() => {
            resetForm()
            setShowForm(true)
          }}
        >
          + Add Medical Record
        </button>
      </div>

      {/* MESSAGES */}

      {error && (
        <div className="medical-alert medical-error">
          {error}
        </div>
      )}

      {success && (
        <div className="medical-alert medical-success">
          {success}
        </div>
      )}

      {/* FORM */}

      {showForm && (
        <div className="medical-form-card">

          <div className="medical-form-header">
            <h2>
              {editingId
                ? "Edit Medical Record"
                : "Create Medical Record"}
            </h2>

            <button
              className="medical-close-btn"
              onClick={resetForm}
              type="button"
            >
              ✕
            </button>
          </div>

          <form onSubmit={handleSubmit}>

            <div className="medical-form-grid">

              {/* PATIENT */}

              <div className="medical-field">
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
                      {patient.full_name ||
                        patient.patient_name ||
                        `Patient ${patient.patient_id}`}
                    </option>
                  ))}
                </select>
              </div>

              {/* DOCTOR */}

              <div className="medical-field">
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
                      {doctor.full_name ||
                        doctor.doctor_name ||
                        `Doctor ${doctor.doctor_id}`}
                    </option>
                  ))}
                </select>
              </div>

              {/* APPOINTMENT */}

              <div className="medical-field">
                <label>Appointment ID</label>

                <input
                  type="number"
                  name="appointment_id"
                  value={form.appointment_id}
                  onChange={handleChange}
                  placeholder="Optional appointment ID"
                  min="1"
                />
              </div>

              {/* DIAGNOSIS */}

              <div className="medical-field">
                <label>Diagnosis *</label>

                <input
                  type="text"
                  name="diagnosis"
                  value={form.diagnosis}
                  onChange={handleChange}
                  placeholder="Enter diagnosis"
                  required
                />
              </div>

              {/* BLOOD PRESSURE */}

              <div className="medical-field">
                <label>Blood Pressure</label>

                <input
                  type="text"
                  name="blood_pressure"
                  value={form.blood_pressure}
                  onChange={handleChange}
                  placeholder="e.g. 118/78"
                />
              </div>

              {/* HEART RATE */}

              <div className="medical-field">
                <label>Heart Rate (bpm)</label>

                <input
                  type="number"
                  name="heart_rate"
                  value={form.heart_rate}
                  onChange={handleChange}
                  placeholder="e.g. 74"
                  min="0"
                />
              </div>

              {/* TEMPERATURE */}

              <div className="medical-field">
                <label>Temperature (°C)</label>

                <input
                  type="number"
                  step="0.1"
                  name="temperature"
                  value={form.temperature}
                  onChange={handleChange}
                  placeholder="e.g. 36.8"
                />
              </div>

              {/* OXYGEN */}

              <div className="medical-field">
                <label>Oxygen Saturation (%)</label>

                <input
                  type="number"
                  name="oxygen_saturation"
                  value={form.oxygen_saturation}
                  onChange={handleChange}
                  min="0"
                  max="100"
                />
              </div>

              {/* HEIGHT */}

              <div className="medical-field">
                <label>Height (cm)</label>

                <input
                  type="number"
                  step="0.1"
                  name="height_cm"
                  value={form.height_cm}
                  onChange={handleChange}
                  placeholder="e.g. 172"
                  min="0"
                />
              </div>

              {/* WEIGHT */}

              <div className="medical-field">
                <label>Weight (kg)</label>

                <input
                  type="number"
                  step="0.1"
                  name="weight_kg"
                  value={form.weight_kg}
                  onChange={handleChange}
                  placeholder="e.g. 68"
                  min="0"
                />
              </div>

            </div>

            {/* CLINICAL NOTES */}

            <div className="medical-field medical-notes-field">
              <label>Clinical Notes</label>

              <textarea
                name="clinical_notes"
                value={form.clinical_notes}
                onChange={handleChange}
                placeholder="Enter clinical notes..."
                rows="4"
              />
            </div>

            {/* BUTTONS */}

            <div className="medical-form-actions">

              <button
                type="button"
                className="medical-secondary-btn"
                onClick={resetForm}
              >
                Cancel
              </button>

              <button
                type="submit"
                className="medical-primary-btn"
              >
                {editingId
                  ? "Update Record"
                  : "Save Record"}
              </button>

            </div>

          </form>
        </div>
      )}

      {/* RECORDS LIST */}

      <div className="medical-records-card">

        <div className="medical-records-toolbar">

          <div>
            <h2>All Medical Records</h2>

            <p>
              {records.length} total records
            </p>
          </div>

          <input
            type="text"
            className="medical-search"
            placeholder="Search patient, doctor, diagnosis..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />

        </div>

        {loading ? (
          <div className="medical-empty">
            Loading medical records...
          </div>
        ) : filteredRecords.length === 0 ? (
          <div className="medical-empty">
            No medical records found.
          </div>
        ) : (

          <div className="medical-table-wrapper">

            <table className="medical-table">

              <thead>
                <tr>
                  <th>Record ID</th>
                  <th>Patient</th>
                  <th>Doctor</th>
                  <th>Diagnosis</th>
                  <th>Recorded At</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>

                {filteredRecords.map((record) => (

                  <tr key={record.record_id}>

                    <td>
                      #{record.record_id}
                    </td>

                    <td>
                      {record.patient_name ||
                        `Patient ${record.patient_id}`}
                    </td>

                    <td>
                      {record.doctor_name ||
                        `Doctor ${record.doctor_id}`}
                    </td>

                    <td>
                      {record.diagnosis}
                    </td>

                    <td>
                      {record.recorded_at
                        ? new Date(
                            record.recorded_at
                          ).toLocaleDateString()
                        : "—"}
                    </td>

                    <td>
                      <div className="medical-action-buttons">

                        <button
                          className="medical-edit-btn"
                          onClick={() => handleEdit(record)}
                        >
                          Edit
                        </button>

                        <button
                          className="medical-delete-btn"
                          onClick={() =>
                            handleDelete(record.record_id)
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