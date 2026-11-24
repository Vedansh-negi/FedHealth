
import { useCallback, useEffect, useState } from 'react'

import {
  Users,
  Search,
  Plus,
  Pencil,
  X,
  RefreshCw,
  UserCheck,
  UserX,
  ShieldCheck,
} from 'lucide-react'

import {
  getUsers,
  createUser,
  updateUser,
  updateUserStatus,
  getSavedUser,
} from '../services/api'

const HOSPITAL_ID = 1

const initialForm = {
  full_name: '',
  email: '',
  password: '',
  role: 'doctor',
}

const roles = [
  { value: 'admin', label: 'Administrator' },
  { value: 'doctor', label: 'Doctor' },
  { value: 'nurse', label: 'Nurse' },
  { value: 'receptionist', label: 'Receptionist' },
  { value: 'lab_technician', label: 'Lab Technician' },
]

export default function UserManagement() {
  const [users, setUsers] = useState([])
  const [search, setSearch] = useState('')

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)

  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  const [showModal, setShowModal] = useState(false)
  const [editingUser, setEditingUser] = useState(null)

  const [form, setForm] = useState(initialForm)

  const currentUser = getSavedUser()

  // --------------------------------------------------
  // LOAD USERS
  // --------------------------------------------------

  const loadUsers = useCallback(async () => {
    setLoading(true)
    setError('')

    try {
      const data = await getUsers(HOSPITAL_ID)

      setUsers(
        Array.isArray(data.users)
          ? data.users
          : []
      )
    } catch (err) {
      setError(err.message || 'Unable to load users.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadUsers()
  }, [loadUsers])

  // --------------------------------------------------
  // OPEN ADD USER MODAL
  // --------------------------------------------------

  function openAddModal() {
    setEditingUser(null)
    setForm(initialForm)
    setError('')
    setSuccess('')
    setShowModal(true)
  }

  // --------------------------------------------------
  // OPEN EDIT USER MODAL
  // --------------------------------------------------

  function openEditModal(user) {
    setEditingUser(user)

    setForm({
      full_name: user.full_name ?? '',
      email: user.email ?? '',
      password: '',
      role: user.role ?? 'doctor',
    })

    setError('')
    setSuccess('')
    setShowModal(true)
  }

  // --------------------------------------------------
  // CLOSE MODAL
  // --------------------------------------------------

  function closeModal() {
    if (saving) return

    setShowModal(false)
    setEditingUser(null)
    setForm(initialForm)
    setError('')
  }

  // --------------------------------------------------
  // HANDLE FORM INPUTS
  // --------------------------------------------------

  function handleChange(event) {
    const { name, value } = event.target

    setForm((previous) => ({
      ...previous,
      [name]: value,
    }))
  }

  // --------------------------------------------------
  // CREATE / UPDATE USER
  // --------------------------------------------------

  async function handleSubmit(event) {
    event.preventDefault()

    setError('')
    setSuccess('')

    const fullName = form.full_name.trim()
    const email = form.email.trim().toLowerCase()

    if (fullName.length < 2) {
      setError('Full name must contain at least 2 characters.')
      return
    }

    if (!email || !email.includes('@')) {
      setError('Please enter a valid email address.')
      return
    }

    if (!editingUser && form.password.length < 8) {
      setError('Password must contain at least 8 characters.')
      return
    }

    const userData = {
      full_name: fullName,
      email,
      role: form.role,
    }

    if (!roles.some((role) => role.value === form.role)) {
      setError('Please select a valid role.')
      return
    }

    if (!editingUser) {
      userData.password = form.password
    }

    setSaving(true)

    try {
      if (editingUser) {
        await updateUser(
          editingUser.user_id,
          userData,
          HOSPITAL_ID
        )

        setSuccess('User updated successfully.')
      } else {
        await createUser(
          userData,
          HOSPITAL_ID
        )

        setSuccess('User created successfully.')
      }

      setShowModal(false)
      setEditingUser(null)
      setForm(initialForm)

      await loadUsers()

    } catch (err) {
      setError(err.message || 'Unable to save user.')
    } finally {
      setSaving(false)
    }
  }

  // --------------------------------------------------
  // ACTIVATE / DEACTIVATE USER
  // --------------------------------------------------

  async function handleStatusChange(user) {
    const isActivating = !user.is_active

    if (
      !isActivating &&
      user.user_id === currentUser?.user_id
    ) {
      setError('You cannot deactivate your own account.')
      return
    }

    const action = isActivating ? 'activate' : 'deactivate'

    const confirmed = window.confirm(
      `Are you sure you want to ${action} ${user.full_name}'s account?`
    )

    if (!confirmed) return

    setError('')
    setSuccess('')

    try {
      await updateUserStatus(
        user.user_id,
        isActivating,
        HOSPITAL_ID
      )

      setSuccess(
        `User ${isActivating ? 'activated' : 'deactivated'} successfully.`
      )

      await loadUsers()

    } catch (err) {
      setError(err.message || 'Unable to update user status.')
    }
  }

  // --------------------------------------------------
  // SEARCH USERS
  // --------------------------------------------------

  const filteredUsers = users.filter((user) => {
    const searchValue = search.toLowerCase()

    return (
      user.full_name?.toLowerCase().includes(searchValue) ||
      user.email?.toLowerCase().includes(searchValue) ||
      user.role?.toLowerCase().includes(searchValue) ||
      String(user.user_id).includes(searchValue)
    )
  })

  // --------------------------------------------------
  // STATISTICS
  // --------------------------------------------------

  const activeUsers = users.filter(
    (user) => user.is_active
  ).length

  const inactiveUsers = users.filter(
    (user) => !user.is_active
  ).length

  // --------------------------------------------------
  // ROLE LABEL
  // --------------------------------------------------

  function getRoleLabel(role) {
    return (
      roles.find((item) => item.value === role)?.label ||
      role
    )
  }

  // --------------------------------------------------
  // PAGE UI
  // --------------------------------------------------

  return (
    <div className="dashboard-page">

      {/* PAGE HEADER */}

      <div className="page-heading">
        <div>
          <p className="eyebrow">HOSPITAL MANAGEMENT</p>

          <h1>User Management</h1>

          <p className="muted">
            Manage staff accounts, permissions and account status.
          </p>
        </div>

        <button
          type="button"
          className="primary-button"
          onClick={openAddModal}
        >
          <Plus size={18} />
          Add User
        </button>
      </div>

      {/* ERROR MESSAGE */}

      {error && !showModal && (
        <div className="doctors-alert error-alert">
          {error}
        </div>
      )}

      {/* SUCCESS MESSAGE */}

      {success && (
        <div className="doctors-alert success-alert">
          {success}
        </div>
      )}

      {/* STATISTICS */}

      <section className="stats-grid">

        <article className="stat-card">
          <div className="stat-icon blue">
            <Users size={21} />
          </div>

          <p className="stat-label">Total Users</p>

          <h2>{users.length}</h2>

          <p className="stat-note">
            Registered in Hospital {HOSPITAL_ID}
          </p>
        </article>

        <article className="stat-card">
          <div className="stat-icon purple">
            <UserCheck size={21} />
          </div>

          <p className="stat-label">Active Users</p>

          <h2>{activeUsers}</h2>

          <p className="stat-note">
            Accounts currently enabled
          </p>
        </article>

        <article className="stat-card">
          <div className="stat-icon">
            <UserX size={21} />
          </div>

          <p className="stat-label">Inactive Users</p>

          <h2>{inactiveUsers}</h2>

          <p className="stat-note">
            Accounts currently disabled
          </p>
        </article>

      </section>

      {/* USERS DIRECTORY */}

      <section className="panel doctors-panel">

        <div className="doctors-toolbar">

          <div>
            <h3>Users Directory</h3>

            <p className="muted">
              View and manage hospital staff accounts.
            </p>
          </div>

          <div className="doctors-actions">

            <div className="doctors-search">
              <Search size={17} />

              <input
                type="text"
                placeholder="Search users..."
                value={search}
                onChange={(event) => setSearch(event.target.value)}
              />
            </div>

            <button
              type="button"
              className="secondary-button"
              onClick={loadUsers}
              disabled={loading}
              title="Refresh users"
            >
              <RefreshCw size={17} />
            </button>

          </div>

        </div>

        {/* TABLE CONTENT */}

        {loading ? (

          <p className="muted doctors-empty">
            Loading users...
          </p>

        ) : filteredUsers.length === 0 ? (

          <div className="doctors-empty">
            <Users size={32} />

            <h3>No users found</h3>

            <p className="muted">
              {search
                ? 'Try a different search.'
                : 'Add a user to get started.'}
            </p>
          </div>

        ) : (

          <div className="table-container">

            <table>

              <thead>
                <tr>
                  <th>User</th>
                  <th>Role</th>
                  <th>Account Status</th>
                  <th>Created At</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>

                {filteredUsers.map((user) => {

                  const isCurrentUser =
                    user.user_id === currentUser?.user_id

                  return (
                    <tr key={user.user_id}>

                      <td>
                        <div className="doctor-name-cell">

                          <div className="doctor-avatar">
                            <Users size={18} />
                          </div>

                          <div>
                            <strong>
                              {user.full_name}

                              {isCurrentUser && ' (You)'}
                            </strong>

                            <span>{user.email}</span>

                            <span>
                              User ID: {user.user_id}
                            </span>
                          </div>

                        </div>
                      </td>

                      <td>
                        <span className="user-role">
                          <ShieldCheck size={14} />
                          {getRoleLabel(user.role)}
                        </span>
                      </td>

                      <td>
                        <span
                          className={
                            user.is_active
                              ? 'user-status active'
                              : 'user-status inactive'
                          }
                        >
                          {user.is_active ? 'Active' : 'Inactive'}
                        </span>
                      </td>

                      <td>
                        {user.created_at
                          ? new Date(user.created_at).toLocaleDateString('en-IN')
                          : 'N/A'}
                      </td>

                      <td>

                        <div className="doctor-action-buttons">

                          <button
                            type="button"
                            className="icon-action edit-action"
                            title="Edit user"
                            onClick={() => openEditModal(user)}
                          >
                            <Pencil size={16} />
                          </button>

                          <button
                            type="button"
                            className={
                              user.is_active
                                ? 'icon-action delete-action'
                                : 'icon-action edit-action'
                            }
                            title={
                              user.is_active
                                ? 'Deactivate user'
                                : 'Activate user'
                            }
                            disabled={isCurrentUser && user.is_active}
                            onClick={() => handleStatusChange(user)}
                          >
                            {user.is_active
                              ? <UserX size={16} />
                              : <UserCheck size={16} />}
                          </button>

                        </div>

                      </td>

                    </tr>
                  )
                })}

              </tbody>

            </table>

          </div>
        )}

        <div className="doctors-table-footer">
          Showing {filteredUsers.length} of {users.length} users
        </div>

      </section>

      {/* ADD / EDIT USER MODAL */}

      {showModal && (

        <div
          className="doctor-modal-overlay"
          onClick={closeModal}
        >

          <div
            className="doctor-modal"
            onClick={(event) => event.stopPropagation()}
          >

            {/* MODAL HEADER */}

            <div className="doctor-modal-header">

              <div>
                <h2>
                  {editingUser ? 'Edit User' : 'Add New User'}
                </h2>

                <p className="muted">
                  {editingUser
                    ? 'Update account details and permissions.'
                    : 'Create a new hospital staff account.'}
                </p>
              </div>

              <button
                type="button"
                className="modal-close-button"
                onClick={closeModal}
                disabled={saving}
              >
                <X size={20} />
              </button>

            </div>

            {/* MODAL ERROR */}

            {error && (
              <div className="doctors-alert error-alert">
                {error}
              </div>
            )}

            {/* USER FORM */}

            <form
              className="doctor-form"
              onSubmit={handleSubmit}
            >

              <div className="doctor-form-grid">

                {/* FULL NAME */}

                <label>
                  Full Name

                  <input
                    name="full_name"
                    type="text"
                    minLength="2"
                    maxLength="100"
                    value={form.full_name}
                    onChange={handleChange}
                    placeholder="Enter full name"
                    required
                  />
                </label>

                {/* EMAIL */}

                <label>
                  Email Address

                  <input
                    name="email"
                    type="email"
                    maxLength="150"
                    value={form.email}
                    onChange={handleChange}
                    placeholder="user@fedhealth.com"
                    required
                  />
                </label>

                {/* PASSWORD - ONLY WHEN CREATING */}

                {!editingUser && (

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

                {/* ROLE */}

                <label>
                  User Role

                  <select
                    name="role"
                    value={form.role}
                    onChange={handleChange}
                    required
                  >
                    {roles.map((role) => (
                      <option
                        key={role.value}
                        value={role.value}
                      >
                        {role.label}
                      </option>
                    ))}
                  </select>
                </label>

              </div>

              <div className="doctor-form-note">
                {editingUser
                  ? 'Changes to a user role take effect immediately. Deactivated accounts cannot access the platform.'
                  : 'The password will be securely hashed before being stored in the hospital database.'}
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
                    : editingUser
                      ? 'Update User'
                      : 'Create User'}
                </button>

              </div>

            </form>

          </div>

        </div>

      )}

    </div>
  )
}

