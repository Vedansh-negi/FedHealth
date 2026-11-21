import { useEffect, useState } from 'react'

import {
  getLabOrders,
  createLabOrder,
  updateLabOrder,
  deleteLabOrder,
  getPatients,
  getDoctors
} from '../services/api'

const HOSPITAL_ID = 1

const emptyForm = {
  patient_id: '',
  doctor_id: '',
  test_name: '',
  priority: 'normal',
  status: 'pending'
}

function LabOrders() {
  const [labOrders, setLabOrders] = useState([])
  const [patients, setPatients] = useState([])
  const [doctors, setDoctors] = useState([])

  const [form, setForm] = useState(emptyForm)
  const [editingId, setEditingId] = useState(null)

  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const loadData = async () => {
    try {
      setLoading(true)
      setError('')

      const [
        labResponse,
        patientResponse,
        doctorResponse
      ] = await Promise.all([
        getLabOrders(HOSPITAL_ID),
        getPatients(HOSPITAL_ID),
        getDoctors(HOSPITAL_ID)
      ])

      setLabOrders(labResponse.lab_orders || [])
      setPatients(patientResponse.patients || [])
      setDoctors(doctorResponse.doctors || [])
    } catch (err) {
      setError(err.message || 'Failed to load lab orders')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadData()
  }, [])

  const handleChange = (e) => {
    const { name, value } = e.target

    setForm((prev) => ({
      ...prev,
      [name]: value
    }))
  }

  const resetForm = () => {
    setForm(emptyForm)
    setEditingId(null)
  }

  const handleSubmit = async (e) => {
    e.preventDefault()

    try {
      setSaving(true)
      setError('')

      const payload = {
        patient_id: Number(form.patient_id),
        doctor_id: Number(form.doctor_id),
        test_name: form.test_name.trim(),
        priority: form.priority,
        status: form.status
      }

      if (editingId) {
        await updateLabOrder(
          editingId,
          payload,
          HOSPITAL_ID
        )
      } else {
        await createLabOrder(
          payload,
          HOSPITAL_ID
        )
      }

      resetForm()
      await loadData()
    } catch (err) {
      setError(err.message || 'Failed to save lab order')
    } finally {
      setSaving(false)
    }
  }

  const handleEdit = (order) => {
    setEditingId(order.lab_order_id)

    setForm({
      patient_id: order.patient_id || '',
      doctor_id: order.doctor_id || '',
      test_name: order.test_name || '',
      priority: order.priority || 'normal',
      status: order.status || 'pending'
    })

    window.scrollTo({
      top: 0,
      behavior: 'smooth'
    })
  }

  const handleDelete = async (orderId) => {
    const confirmed = window.confirm(
      'Are you sure you want to delete this lab order?'
    )

    if (!confirmed) return

    try {
      setError('')

      await deleteLabOrder(
        orderId,
        HOSPITAL_ID
      )

      await loadData()
    } catch (err) {
      setError(err.message || 'Failed to delete lab order')
    }
  }

  const filteredOrders = labOrders.filter((order) => {
    const searchText = search.toLowerCase()

    const matchesSearch =
      order.patient_name?.toLowerCase().includes(searchText) ||
      order.doctor_name?.toLowerCase().includes(searchText) ||
      order.test_name?.toLowerCase().includes(searchText)

    const matchesStatus =
      statusFilter === 'all' ||
      order.status === statusFilter

    return matchesSearch && matchesStatus
  })

  const getStatusClass = (status) => {
    return `lab-status lab-status-${status}`
  }

  const getPriorityClass = (priority) => {
    return `lab-priority lab-priority-${priority}`
  }

  return (
    <div className="lab-orders-page">

      {/* Header */}
      <div className="lab-orders-header">
        <div>
          <h1>Lab Orders</h1>
          <p>Manage laboratory tests and orders</p>
        </div>

        <div className="lab-orders-count">
          <span>{labOrders.length}</span>
          <small>Total Lab Orders</small>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="lab-orders-error">
          {error}
        </div>
      )}

      {/* Form */}
      <div className="lab-order-form-card">

        <div className="lab-order-form-heading">
          <h2>
            {editingId
              ? 'Edit Lab Order'
              : 'Create Lab Order'}
          </h2>

          {editingId && (
            <button
              type="button"
              className="lab-cancel-btn"
              onClick={resetForm}
            >
              Cancel Edit
            </button>
          )}
        </div>

        <form onSubmit={handleSubmit}>

          <div className="lab-order-form-grid">

            <div className="lab-order-field">
              <label>Patient *</label>

              <select
                name="patient_id"
                value={form.patient_id}
                onChange={handleChange}
                required
              >
                <option value="">Select Patient</option>

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

            <div className="lab-order-field">
              <label>Doctor *</label>

              <select
                name="doctor_id"
                value={form.doctor_id}
                onChange={handleChange}
                required
              >
                <option value="">Select Doctor</option>

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

            <div className="lab-order-field">
              <label>Test Name *</label>

              <input
                type="text"
                name="test_name"
                value={form.test_name}
                onChange={handleChange}
                placeholder="e.g. Complete Blood Count"
                required
              />
            </div>

            <div className="lab-order-field">
              <label>Priority *</label>

              <select
                name="priority"
                value={form.priority}
                onChange={handleChange}
                required
              >
                <option value="normal">Normal</option>
                <option value="urgent">Urgent</option>
                <option value="stat">Stat</option>
              </select>
            </div>

            <div className="lab-order-field">
              <label>Status *</label>

              <select
                name="status"
                value={form.status}
                onChange={handleChange}
                required
              >
                <option value="pending">Pending</option>
                <option value="sample_collected">
                  Sample Collected
                </option>
                <option value="in_progress">
                  In Progress
                </option>
                <option value="completed">Completed</option>
                <option value="cancelled">Cancelled</option>
              </select>
            </div>

          </div>

          <div className="lab-order-form-actions">

            <button
              type="submit"
              className="lab-submit-btn"
              disabled={saving}
            >
              {saving
                ? 'Saving...'
                : editingId
                  ? 'Update Lab Order'
                  : 'Create Lab Order'}
            </button>

            <button
              type="button"
              className="lab-reset-btn"
              onClick={resetForm}
            >
              Reset
            </button>

          </div>

        </form>
      </div>

      {/* List */}
      <div className="lab-order-list-card">

        <div className="lab-order-list-heading">
          <div>
            <h2>All Lab Orders</h2>
            <p>View and manage laboratory test requests</p>
          </div>

          <div className="lab-order-filters">

            <input
              type="text"
              placeholder="Search patient or test..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
            >
              <option value="all">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="sample_collected">
                Sample Collected
              </option>
              <option value="in_progress">In Progress</option>
              <option value="completed">Completed</option>
              <option value="cancelled">Cancelled</option>
            </select>

          </div>
        </div>

        {loading ? (
          <div className="lab-order-empty">
            Loading lab orders...
          </div>
        ) : filteredOrders.length === 0 ? (
          <div className="lab-order-empty">
            No lab orders found.
          </div>
        ) : (
          <div className="lab-order-table-wrapper">

            <table className="lab-order-table">

              <thead>
                <tr>
                  <th>Order ID</th>
                  <th>Patient</th>
                  <th>Doctor</th>
                  <th>Test</th>
                  <th>Priority</th>
                  <th>Status</th>
                  <th>Ordered At</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {filteredOrders.map((order) => (
                  <tr key={order.lab_order_id}>

                    <td>#{order.lab_order_id}</td>

                    <td>
                      <strong>{order.patient_name}</strong>
                    </td>

                    <td>{order.doctor_name}</td>

                    <td>
                      <span className="lab-test-name">
                        {order.test_name}
                      </span>
                    </td>

                    <td>
                      <span className={getPriorityClass(order.priority)}>
                        {order.priority}
                      </span>
                    </td>

                    <td>
                      <span className={getStatusClass(order.status)}>
                        {order.status?.replaceAll('_', ' ')}
                      </span>
                    </td>

                    <td>
                      {order.ordered_at
                        ? new Date(order.ordered_at).toLocaleDateString()
                        : '-'}
                    </td>

                    <td>
                      <div className="lab-order-actions">

                        <button
                          type="button"
                          className="lab-edit-btn"
                          onClick={() => handleEdit(order)}
                        >
                          Edit
                        </button>

                        <button
                          type="button"
                          className="lab-delete-btn"
                          onClick={() =>
                            handleDelete(order.lab_order_id)
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

export default LabOrders