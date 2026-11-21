import { useCallback, useEffect, useState } from 'react'

import {
  Search,
  Plus,
  Pencil,
  Trash2,
  X,
  CalendarDays,
  RefreshCw,
  Clock,
} from 'lucide-react'

import {
  getAppointments,
  createAppointment,
  updateAppointment,
  deleteAppointment,
  getPatients,
  getDoctors,
} from '../services/api'

const HOSPITAL_ID = 1

const initialForm = {
  patient_id: '',
  doctor_id: '',
  appointment_date: '',
  appointment_time: '',
  reason: '',
  status: 'scheduled',
}

export default function Appointments() {
  const [appointments, setAppointments] = useState([])
  const [patients, setPatients] = useState([])
  const [doctors, setDoctors] = useState([])

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [showModal, setShowModal] = useState(false)
  const [editingAppointment, setEditingAppointment] = useState(null)

  const [form, setForm] = useState(initialForm)

  // =========================
  // LOAD APPOINTMENTS
  // =========================

  const loadAppointments = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      const data = await getAppointments(HOSPITAL_ID)

      setAppointments(
        Array.isArray(data.appointments)
          ? data.appointments
          : []
      )
    } catch (err) {
      setError(
        err.message || 'Failed to load appointments.'
      )
    } finally {
      setLoading(false)
    }
  }, [])

  // =========================
  // LOAD PATIENTS AND DOCTORS
  // =========================

  const loadFormData = useCallback(async () => {
    try {
      const [patientData, doctorData] = await Promise.all([
        getPatients(HOSPITAL_ID),
        getDoctors(HOSPITAL_ID),
      ])

      setPatients(
        Array.isArray(patientData.patients)
          ? patientData.patients
          : []
      )

      setDoctors(
        Array.isArray(doctorData.doctors)
          ? doctorData.doctors
          : []
      )
    } catch (err) {
      setError(
        err.message || 'Failed to load patients and doctors.'
      )
    }
  }, [])

  useEffect(() => {
    loadAppointments()
    loadFormData()
  }, [loadAppointments, loadFormData])

  // =========================
  // OPEN ADD MODAL
  // =========================

  function openAddModal() {
    setEditingAppointment(null)
    setForm(initialForm)

    setError('')
    setSuccess('')

    setShowModal(true)
  }

  // =========================
  // OPEN EDIT MODAL
  // =========================

  function openEditModal(appointment) {
    setEditingAppointment(appointment)

    setForm({
      patient_id: String(appointment.patient_id ?? ''),
      doctor_id: String(appointment.doctor_id ?? ''),

      appointment_date: appointment.appointment_date
        ? String(appointment.appointment_date).slice(0, 10)
        : '',

      appointment_time: appointment.appointment_time
        ? String(appointment.appointment_time).slice(0, 5)
        : '',

      reason: appointment.reason ?? '',

      status: appointment.status ?? 'scheduled',
    })

    setError('')
    setSuccess('')

    setShowModal(true)
  }

  // =========================
  // CLOSE MODAL
  // =========================

  function closeModal() {
    setShowModal(false)

    setEditingAppointment(null)
    setForm(initialForm)

    setError('')
  }

  // =========================
  // HANDLE FORM CHANGE
  // =========================

  function handleChange(event) {
    const { name, value } = event.target

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }))
  }

  // =========================
  // CREATE / UPDATE
  // =========================

  async function handleSubmit(event) {
    event.preventDefault()

    setError('')
    setSuccess('')

    const appointmentData = {
      patient_id: Number(form.patient_id),
      doctor_id: Number(form.doctor_id),

      appointment_date: form.appointment_date,
      appointment_time: form.appointment_time,

      reason: form.reason.trim(),
      status: form.status,
    }

    if (
      !appointmentData.patient_id ||
      !appointmentData.doctor_id ||
      !appointmentData.appointment_date ||
      !appointmentData.appointment_time ||
      !appointmentData.reason
    ) {
      setError('Please fill all required fields.')
      return
    }

    setSaving(true)

    try {
      if (editingAppointment) {
        await updateAppointment(
          editingAppointment.appointment_id,
          appointmentData,
          HOSPITAL_ID
        )

        setSuccess('Appointment updated successfully.')
      } else {
        await createAppointment(
          appointmentData,
          HOSPITAL_ID
        )

        setSuccess('Appointment created successfully.')
      }

      closeModal()

      await loadAppointments()
    } catch (err) {
      setError(
        err.message || 'Failed to save appointment.'
      )
    } finally {
      setSaving(false)
    }
  }

  // =========================
  // DELETE APPOINTMENT
  // =========================

  async function handleDelete(appointment) {
    const confirmed = window.confirm(
      'Are you sure you want to delete this appointment?'
    )

    if (!confirmed) return

    setError('')
    setSuccess('')

    try {
      await deleteAppointment(
        appointment.appointment_id,
        HOSPITAL_ID
      )

      setSuccess('Appointment deleted successfully.')

      await loadAppointments()
    } catch (err) {
      setError(
        err.message || 'Failed to delete appointment.'
      )
    }
  }

  // =========================
  // SEARCH AND FILTER
  // =========================

  const filteredAppointments = appointments.filter(
    (appointment) => {
      const searchValue = search.toLowerCase()

      const patientName = String(
        appointment.patient_name || ''
      ).toLowerCase()

      const doctorName = String(
        appointment.doctor_name || ''
      ).toLowerCase()

      const reason = String(
        appointment.reason || ''
      ).toLowerCase()

      const matchesSearch =
        patientName.includes(searchValue) ||
        doctorName.includes(searchValue) ||
        reason.includes(searchValue)

      const matchesStatus =
        statusFilter === 'all' ||
        appointment.status === statusFilter

      return matchesSearch && matchesStatus
    }
  )

  // =========================
  // FORMAT STATUS
  // =========================

  function formatStatus(status) {
    if (!status) return 'Scheduled'

    return status
      .replaceAll('_', ' ')
      .replace(/\b\w/g, (letter) => letter.toUpperCase())
  }

  // =========================
  // FORMAT DOCTOR NAME
  // =========================

  function formatDoctorName(name, doctorId) {
    if (!name) {
      return `Doctor #${doctorId}`
    }

    return name.startsWith('Dr.')
      ? name
      : `Dr. ${name}`
  }

  // =========================
  // RENDER
  // =========================

  return (
    <div className="dashboard-page">

      {/* PAGE HEADER */}

      <div className="page-heading">

        <div>
          <p className="eyebrow">
            HOSPITAL MANAGEMENT
          </p>

          <h1>Appointments</h1>

          <p className="muted">
            Schedule and manage patient appointments.
          </p>
        </div>

        <button
          type="button"
          className="primary-button"
          onClick={openAddModal}
        >
          <Plus size={18} />
          Add Appointment
        </button>

      </div>

      {/* ALERTS */}

      {error && !showModal && (
        <div className="doctors-alert error-alert">
          {error}
        </div>
      )}

      {success && (
        <div className="doctors-alert success-alert">
          {success}
        </div>
      )}

      {/* STATISTICS */}

      <section className="stats-grid">

        <article className="stat-card">

          <div className="stat-icon blue">
            <CalendarDays size={21} />
          </div>

          <p className="stat-label">
            Total Appointments
          </p>

          <h2>{appointments.length}</h2>

          <p className="stat-note">
            Hospital {HOSPITAL_ID}
          </p>

        </article>

        <article className="stat-card">

          <div className="stat-icon purple">
            <Clock size={21} />
          </div>

          <p className="stat-label">
            Scheduled
          </p>

          <h2>
            {
              appointments.filter(
                (appointment) =>
                  appointment.status === 'scheduled'
              ).length
            }
          </h2>

          <p className="stat-note">
            Upcoming appointments
          </p>

        </article>

      </section>

      {/* APPOINTMENTS TABLE */}

      <section className="panel doctors-panel">

        <div className="doctors-toolbar">

          <div>
            <h3>Appointment Records</h3>

            <p className="muted">
              View and manage hospital appointments.
            </p>
          </div>

          <div className="doctors-actions">

            {/* SEARCH */}

            <div className="doctors-search">

              <Search size={17} />

              <input
                type="text"
                placeholder="Search appointments..."
                value={search}
                onChange={(event) =>
                  setSearch(event.target.value)
                }
              />

            </div>

            {/* STATUS FILTER */}

            <select
              className="appointment-status-filter"
              value={statusFilter}
              onChange={(event) =>
                setStatusFilter(event.target.value)
              }
            >
              <option value="all">
                All Status
              </option>

              <option value="scheduled">
                Scheduled
              </option>

              <option value="completed">
                Completed
              </option>

              <option value="cancelled">
                Cancelled
              </option>

              <option value="no_show">
                No Show
              </option>

            </select>

            {/* REFRESH */}

            <button
              type="button"
              className="secondary-button"
              onClick={loadAppointments}
              disabled={loading}
              title="Refresh appointments"
            >
              <RefreshCw size={17} />
            </button>

          </div>

        </div>

        {/* LOADING */}

        {loading ? (
          <div className="doctors-empty">
            <RefreshCw size={24} />

            <p>Loading appointments...</p>
          </div>
        ) : filteredAppointments.length === 0 ? (

          /* EMPTY STATE */

          <div className="doctors-empty">

            <CalendarDays size={32} />

            <h3>No appointments found</h3>

            <p className="muted">
              {search || statusFilter !== 'all'
                ? 'Try changing your search or status filter.'
                : 'Add an appointment to get started.'}
            </p>

          </div>

        ) : (

          /* TABLE */

          <div className="table-container">

            <table>

              <thead>
                <tr>
                  <th>Patient</th>
                  <th>Doctor</th>
                  <th>Date</th>
                  <th>Time</th>
                  <th>Reason</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>

                {filteredAppointments.map((appointment) => (

                  <tr key={appointment.appointment_id}>

                    {/* PATIENT */}

                    <td>
                      <strong>
                        {appointment.patient_name ||
                          `Patient #${appointment.patient_id}`}
                      </strong>
                    </td>

                    {/* DOCTOR */}

                    <td>
                      {formatDoctorName(
                        appointment.doctor_name,
                        appointment.doctor_id
                      )}
                    </td>

                    {/* DATE */}

                    <td>
                      {appointment.appointment_date
                        ? String(
                            appointment.appointment_date
                          ).slice(0, 10)
                        : '-'}
                    </td>

                    {/* TIME */}

                    <td>
                      {appointment.appointment_time
                        ? String(
                            appointment.appointment_time
                          ).slice(0, 5)
                        : '-'}
                    </td>

                    {/* REASON */}

                    <td>
                      {appointment.reason || '-'}
                    </td>

                    {/* STATUS */}

                    <td>
                      <span
                        className={`appointment-status status-${appointment.status}`}
                      >
                        {formatStatus(appointment.status)}
                      </span>
                    </td>

                    {/* ACTIONS */}

                    <td>

                      <div className="doctor-action-buttons">

                        <button
                          type="button"
                          className="icon-action edit-action"
                          title="Edit appointment"
                          onClick={() =>
                            openEditModal(appointment)
                          }
                        >
                          <Pencil size={16} />
                        </button>

                        <button
                          type="button"
                          className="icon-action delete-action"
                          title="Delete appointment"
                          onClick={() =>
                            handleDelete(appointment)
                          }
                        >
                          <Trash2 size={16} />
                        </button>

                      </div>

                    </td>

                  </tr>

                ))}

              </tbody>

            </table>

          </div>

        )}

        {/* TABLE FOOTER */}

        <div className="doctors-table-footer">
          Showing {filteredAppointments.length} of{' '}
          {appointments.length} appointments
        </div>

      </section>

      {/* ADD / EDIT MODAL */}

      {showModal && (

        <div
          className="doctor-modal-overlay"
          onClick={closeModal}
        >

          <div
            className="doctor-modal"
            onClick={(event) =>
              event.stopPropagation()
            }
          >

            {/* MODAL HEADER */}

            <div className="doctor-modal-header">

              <div>
                <h2>
                  {editingAppointment
                    ? 'Edit Appointment'
                    : 'Add New Appointment'}
                </h2>

                <p className="muted">
                  Enter appointment details below.
                </p>
              </div>

              <button
                type="button"
                className="modal-close-button"
                onClick={closeModal}
              >
                <X size={20} />
              </button>

            </div>

            {/* FORM ERROR */}

            {error && (
              <div className="doctors-alert error-alert">
                {error}
              </div>
            )}

            {/* FORM */}

            <form
              className="doctor-form"
              onSubmit={handleSubmit}
            >

              <div className="doctor-form-grid">

                {/* PATIENT */}

                <label>
                  Patient

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
                        {patient.full_name}
                      </option>

                    ))}

                  </select>
                </label>

                {/* DOCTOR */}

                <label>
                  Doctor

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
                        {formatDoctorName(
                          doctor.full_name,
                          doctor.doctor_id
                        )}
                      </option>

                    ))}

                  </select>
                </label>

                {/* DATE */}

                <label>
                  Appointment Date

                  <input
                    type="date"
                    name="appointment_date"
                    value={form.appointment_date}
                    onChange={handleChange}
                    required
                  />
                </label>

                {/* TIME */}

                <label>
                  Appointment Time

                  <input
                    type="time"
                    name="appointment_time"
                    value={form.appointment_time}
                    onChange={handleChange}
                    required
                  />
                </label>

                {/* STATUS */}

                <label>
                  Status

                  <select
                    name="status"
                    value={form.status}
                    onChange={handleChange}
                    required
                  >
                    <option value="scheduled">
                      Scheduled
                    </option>

                    <option value="completed">
                      Completed
                    </option>

                    <option value="cancelled">
                      Cancelled
                    </option>

                    <option value="no_show">
                      No Show
                    </option>

                  </select>
                </label>

                {/* REASON */}

                <label>
                  Reason

                  <input
                    type="text"
                    name="reason"
                    maxLength="255"
                    value={form.reason}
                    onChange={handleChange}
                    placeholder="e.g. General checkup"
                    required
                  />
                </label>

              </div>

              {/* MODAL FOOTER */}

              <div className="doctor-modal-footer">

                <button
                  type="button"
                  className="secondary-button"
                  onClick={closeModal}
                  disabled={saving}
                >
                  Cancel
                </button>

                <button
                  type="submit"
                  className="primary-button"
                  disabled={saving}
                >
                  {saving
                    ? 'Saving...'
                    : editingAppointment
                      ? 'Update Appointment'
                      : 'Create Appointment'}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}

    </div>
  )
}