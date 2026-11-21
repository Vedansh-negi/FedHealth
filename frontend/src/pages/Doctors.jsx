
import { useCallback, useEffect, useState } from 'react'
import {
  Users,
  Search,
  Plus,
  Pencil,
  Trash2,
  X,
  RefreshCw,
  Stethoscope,
} from 'lucide-react'

import {
  getDoctors,
  getDoctorDepartments,
  createDoctor,
  updateDoctor,
  deleteDoctor,
} from '../services/api'

const HOSPITAL_ID = 1

const initialForm = {
  full_name: '',
  email: '',
  password: '',
  department_id: '',
  specialization: '',
  qualification: '',
  license_number: '',
  consultation_fee: '',
}

export default function Doctors() {
  const [doctors, setDoctors] = useState([])
  const [departments, setDepartments] = useState([])
  const [search, setSearch] = useState('')

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [showModal, setShowModal] = useState(false)
  const [editingDoctor, setEditingDoctor] = useState(null)
  const [form, setForm] = useState(initialForm)
  const [saving, setSaving] = useState(false)

  // Load doctors
  const loadDoctors = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      const data = await getDoctors(HOSPITAL_ID)

      setDoctors(
        Array.isArray(data.doctors)
          ? data.doctors
          : []
      )
    } catch (err) {
      setError(
        err.message || 'Doctors load nahi ho paaye'
      )
    } finally {
      setLoading(false)
    }
  }, [])

  // Load departments
  const loadDepartments = useCallback(async () => {
    try {
      const data = await getDoctorDepartments(HOSPITAL_ID)

      setDepartments(
        Array.isArray(data.departments)
          ? data.departments
          : []
      )
    } catch (err) {
      setError(
        err.message || 'Departments load nahi ho paaye'
      )
    }
  }, [])

  useEffect(() => {
    loadDoctors()
    loadDepartments()
  }, [loadDoctors, loadDepartments])

  // Open Add Doctor modal
  function openAddModal() {
    setEditingDoctor(null)
    setForm(initialForm)
    setError('')
    setSuccess('')
    setShowModal(true)
  }

  // Open Edit Doctor modal
  function openEditModal(doctor) {
    setEditingDoctor(doctor)

    setForm({
      full_name: doctor.full_name ?? '',
      email: doctor.email ?? '',
      password: '',
      department_id: String(
        doctor.department_id ?? ''
      ),
      specialization: doctor.specialization ?? '',
      qualification: doctor.qualification ?? '',
      license_number: doctor.license_number ?? '',
      consultation_fee: String(
        doctor.consultation_fee ?? ''
      ),
    })

    setError('')
    setSuccess('')
    setShowModal(true)
  }

  // Close modal
  function closeModal() {
    setShowModal(false)
    setEditingDoctor(null)
    setForm(initialForm)
    setError('')
  }

  // Form input handler
  function handleChange(event) {
    const { name, value } = event.target

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }))
  }

  // Add or update doctor
  async function handleSubmit(event) {
    event.preventDefault()

    setError('')
    setSuccess('')

    const doctorData = {
      department_id: Number(form.department_id),
      specialization: form.specialization.trim(),
      qualification: form.qualification.trim(),
      license_number: form.license_number.trim(),
      consultation_fee: Number(form.consultation_fee),
    }

    // Add Doctor: include user account fields
    if (!editingDoctor) {
      doctorData.full_name = form.full_name.trim()
      doctorData.email = form.email.trim()
      doctorData.password = form.password
    }

    // Validate required fields
    if (
      !doctorData.department_id ||
      !doctorData.specialization ||
      !doctorData.qualification ||
      !doctorData.license_number ||
      form.consultation_fee === '' ||
      Number.isNaN(doctorData.consultation_fee) ||
      doctorData.consultation_fee < 0
    ) {
      setError('Please enter valid details in all fields.')
      return
    }

    // Validate new doctor account fields
    if (!editingDoctor) {
      if (
        !doctorData.full_name ||
        !doctorData.email ||
        !doctorData.password
      ) {
        setError('Please enter name, email and password.')
        return
      }

      if (doctorData.password.length < 8) {
        setError('Password must contain at least 8 characters.')
        return
      }
    }

    setSaving(true)

    try {
      if (editingDoctor) {
        await updateDoctor(
          editingDoctor.doctor_id,
          doctorData,
          HOSPITAL_ID
        )

        setSuccess('Doctor updated successfully.')
      } else {
        await createDoctor(
          doctorData,
          HOSPITAL_ID
        )

        setSuccess('Doctor added successfully.')
      }

      closeModal()
      await loadDoctors()
    } catch (err) {
      setError(
        err.message || 'Doctor save nahi ho paaya'
      )
    } finally {
      setSaving(false)
    }
  }

  // Delete doctor
  async function handleDelete(doctor) {
    const confirmed = window.confirm(
      `Are you sure you want to delete Dr. ${doctor.full_name}?`
    )

    if (!confirmed) return

    setError('')
    setSuccess('')

    try {
      await deleteDoctor(
        doctor.doctor_id,
        HOSPITAL_ID
      )

      setSuccess('Doctor deleted successfully.')
      await loadDoctors()
    } catch (err) {
      setError(
        err.message || 'Doctor delete nahi ho paaya'
      )
    }
  }

  // Search doctors
  const filteredDoctors = doctors.filter((doctor) => {
    const searchValue = search.toLowerCase()

    return (
      doctor.full_name?.toLowerCase().includes(searchValue) ||
      doctor.email?.toLowerCase().includes(searchValue) ||
      doctor.specialization?.toLowerCase().includes(searchValue) ||
      doctor.department_name?.toLowerCase().includes(searchValue) ||
      doctor.license_number?.toLowerCase().includes(searchValue)
    )
  })

  return (
    <div className="dashboard-page">

      {/* Page Header */}
      <div className="page-heading">
        <div>
          <p className="eyebrow">HOSPITAL MANAGEMENT</p>

          <h1>Doctors</h1>

          <p className="muted">
            Manage doctors and their professional details.
          </p>
        </div>

        <button
          type="button"
          className="primary-button"
          onClick={openAddModal}
        >
          <Plus size={18} />
          Add Doctor
        </button>
      </div>

      {/* Error Message */}
      {error && !showModal && (
        <div className="doctors-alert error-alert">
          {error}
        </div>
      )}

      {/* Success Message */}
      {success && (
        <div className="doctors-alert success-alert">
          {success}
        </div>
      )}

      {/* Statistics */}
      <section className="stats-grid">

        <article className="stat-card">
          <div className="stat-icon blue">
            <Users size={21} />
          </div>

          <p className="stat-label">Total Doctors</p>

          <h2>{doctors.length}</h2>

          <p className="stat-note">
            Registered in Hospital {HOSPITAL_ID}
          </p>
        </article>

        <article className="stat-card">
          <div className="stat-icon purple">
            <Stethoscope size={21} />
          </div>

          <p className="stat-label">Specializations</p>

          <h2>
            {
              new Set(
                doctors.map((doctor) => doctor.specialization)
              ).size
            }
          </h2>

          <p className="stat-note">
            Unique medical specializations
          </p>
        </article>

      </section>

      {/* Doctors Directory */}
      <section className="panel doctors-panel">

        <div className="doctors-toolbar">
          <div>
            <h3>Doctors Directory</h3>

            <p className="muted">
              View and manage registered doctors.
            </p>
          </div>

          <div className="doctors-actions">

            <div className="doctors-search">
              <Search size={17} />

              <input
                type="text"
                placeholder="Search doctors..."
                value={search}
                onChange={(event) =>
                  setSearch(event.target.value)
                }
              />
            </div>

            <button
              type="button"
              className="secondary-button"
              onClick={loadDoctors}
              disabled={loading}
              title="Refresh doctors"
            >
              <RefreshCw size={17} />
            </button>

          </div>
        </div>

        {loading ? (
          <p className="muted doctors-empty">
            Loading doctors...
          </p>
        ) : filteredDoctors.length === 0 ? (
          <div className="doctors-empty">
            <Users size={32} />

            <h3>No doctors found</h3>

            <p className="muted">
              {search
                ? 'Try a different search.'
                : 'Add a doctor to get started.'}
            </p>
          </div>
        ) : (
          <div className="table-container">

            <table>
              <thead>
                <tr>
                  <th>Doctor</th>
                  <th>Department</th>
                  <th>Specialization</th>
                  <th>Qualification</th>
                  <th>Consultation Fee</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {filteredDoctors.map((doctor) => (
                  <tr key={doctor.doctor_id}>
                    <td>
                      <div className="doctor-name-cell">

                        <div className="doctor-avatar">
                          <Stethoscope size={18} />
                        </div>

                        <div>
                          <strong>
                            {doctor.full_name}
                          </strong>

                          <span>
                            {doctor.email}
                          </span>
                        </div>

                      </div>
                    </td>

                    <td>
                      {doctor.department_name || 'N/A'}
                    </td>

                    <td>
                      {doctor.specialization || 'N/A'}
                    </td>

                    <td>
                      {doctor.qualification || 'N/A'}
                    </td>

                    <td>
                      ₹
                      {Number(
                        doctor.consultation_fee || 0
                      ).toLocaleString('en-IN')}
                    </td>

                    <td>
                      <div className="doctor-action-buttons">

                        <button
                          type="button"
                          className="icon-action edit-action"
                          title="Edit doctor"
                          onClick={() =>
                            openEditModal(doctor)
                          }
                        >
                          <Pencil size={16} />
                        </button>

                        <button
                          type="button"
                          className="icon-action delete-action"
                          title="Delete doctor"
                          onClick={() =>
                            handleDelete(doctor)
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

        <div className="doctors-table-footer">
          Showing {filteredDoctors.length} of {doctors.length} doctors
        </div>

      </section>

      {/* Add / Edit Doctor Modal */}
      {showModal && (
        <div
          className="doctor-modal-overlay"
          onClick={closeModal}
        >
          <div
            className="doctor-modal"
            onClick={(event) => event.stopPropagation()}
          >

            {/* Modal Header */}
            <div className="doctor-modal-header">
              <div>
                <h2>
                  {editingDoctor
                    ? 'Edit Doctor'
                    : 'Add New Doctor'}
                </h2>

                <p className="muted">
                  {editingDoctor
                    ? 'Update professional details.'
                    : 'Enter doctor account and professional details.'}
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

            {/* Modal Error */}
            {error && (
              <div className="doctors-alert error-alert">
                {error}
              </div>
            )}

            {/* Doctor Form */}
            <form
              className="doctor-form"
              onSubmit={handleSubmit}
            >

              <div className="doctor-form-grid">

                {/* Full Name */}
                {!editingDoctor && (
                  <label>
                    Full Name

                    <input
                      name="full_name"
                      type="text"
                      maxLength="100"
                      value={form.full_name}
                      onChange={handleChange}
                      placeholder="e.g. Dr Amit Sharma"
                      required
                    />
                  </label>
                )}

                {/* Email */}
                {!editingDoctor && (
                  <label>
                    Email Address

                    <input
                      name="email"
                      type="email"
                      maxLength="150"
                      value={form.email}
                      onChange={handleChange}
                      placeholder="doctor@fedhealth.com"
                      required
                    />
                  </label>
                )}

                {/* Password */}
                {!editingDoctor && (
                  <label>
                    Password

                    <input
                      name="password"
                      type="password"
                      minLength="8"
                      maxLength="100"
                      value={form.password}
                      onChange={handleChange}
                      placeholder="Minimum 8 characters"
                      required
                    />
                  </label>
                )}

                {/* Department Dropdown */}
                <label>
                  Department

                  <select
                    name="department_id"
                    value={form.department_id}
                    onChange={handleChange}
                    required
                  >
                    <option value="">
                      Select Department
                    </option>

                    {departments.map((department) => (
                      <option
                        key={department.department_id}
                        value={department.department_id}
                      >
                        {department.department_name}
                      </option>
                    ))}
                  </select>
                </label>

                {/* Specialization */}
                <label>
                  Specialization

                  <input
                    name="specialization"
                    type="text"
                    maxLength="100"
                    value={form.specialization}
                    onChange={handleChange}
                    placeholder="e.g. Cardiology"
                    required
                  />
                </label>

                {/* Qualification */}
                <label>
                  Qualification

                  <input
                    name="qualification"
                    type="text"
                    maxLength="100"
                    value={form.qualification}
                    onChange={handleChange}
                    placeholder="e.g. MBBS, MD"
                    required
                  />
                </label>

                {/* License */}
                <label>
                  License Number

                  <input
                    name="license_number"
                    type="text"
                    maxLength="100"
                    value={form.license_number}
                    onChange={handleChange}
                    placeholder="Enter medical license"
                    required
                  />
                </label>

                {/* Consultation Fee */}
                <label>
                  Consultation Fee (₹)

                  <input
                    name="consultation_fee"
                    type="number"
                    min="0"
                    step="0.01"
                    value={form.consultation_fee}
                    onChange={handleChange}
                    placeholder="e.g. 500"
                    required
                  />
                </label>

              </div>

              <div className="doctor-form-note">
                {editingDoctor
                  ? 'You can update the doctor’s professional details here.'
                  : 'A doctor account will be created automatically. The password will be securely hashed.'}
              </div>

              {/* Modal Footer */}
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
                    : editingDoctor
                      ? 'Update Doctor'
                      : 'Add Doctor'}
                </button>

              </div>

            </form>

          </div>
        </div>
      )}

    </div>
  )
}
