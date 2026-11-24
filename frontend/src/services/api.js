
const API_BASE_URL = 'http://127.0.0.1:8000'

// ================= AUTH =================

export const getToken = () => {
  return localStorage.getItem('token')
}

export const getSavedUser = () => {
  const user = localStorage.getItem('user')
  return user ? JSON.parse(user) : null
}

export const loginUser = async (email, password, hospitalId = 1) => {
  const response = await fetch(
    `${API_BASE_URL}/api/auth/login?hospital_id=${hospitalId}`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    }
  )

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || 'Login failed')
  }

  localStorage.setItem('token', data.access_token)

  if (data.user) {
    localStorage.setItem('user', JSON.stringify(data.user))
  }

  return data
}

export const logoutUser = () => {
  localStorage.removeItem('token')
  localStorage.removeItem('user')
}

// ================= COMMON API FUNCTIONS =================

// Token expired / invalid: clear the session and go back to login.
const handleUnauthorized = () => {
  logoutUser()

  if (window.location.pathname !== '/login') {
    window.location.replace('/login')
  }
}

export const fetchAPI = async (endpoint) => {
  const token = getToken()

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
      ...(token && {
        Authorization: `Bearer ${token}`,
      }),
    },
  })

  const data = await response.json().catch(() => null)

  if (response.status === 401) {
    handleUnauthorized()
  }

  if (!response.ok) {
    const detail = data?.detail
    throw new Error(
      typeof detail === 'string' ? detail : 'API request failed'
    )
  }

  return data
}

export const sendAPIRequest = async (
  endpoint,
  method,
  body = null
) => {
  const token = getToken()

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...(token && {
        Authorization: `Bearer ${token}`,
      }),
    },
    ...(body !== null && {
      body: JSON.stringify(body),
    }),
  })

  const data = await response.json().catch(() => null)

  if (response.status === 401) {
    handleUnauthorized()
  }

  if (!response.ok) {
    const detail = data?.detail
    throw new Error(
      typeof detail === 'string' ? detail : 'API request failed'
    )
  }

  return data
}

// ================= DASHBOARD API =================

export const getDashboardData = () => {
  return fetchAPI('/api/dashboard')
}

// ================= HOSPITALS API =================

export const getHospitals = () => {
  return fetchAPI('/api/hospitals')
}

// ================= PATIENTS API =================

export const getPatients = (hospitalId = 1) => {
  return fetchAPI(`/api/patients/?hospital_id=${hospitalId}`)
}

export const getPatientById = (
  patientId,
  hospitalId = 1
) => {
  return fetchAPI(
    `/api/patients/${patientId}?hospital_id=${hospitalId}`
  )
}

export const createPatient = (
  patientData,
  hospitalId = 1
) => {
  return sendAPIRequest(
    `/api/patients/?hospital_id=${hospitalId}`,
    'POST',
    patientData
  )
}

export const updatePatient = (
  patientId,
  patientData,
  hospitalId = 1
) => {
  return sendAPIRequest(
    `/api/patients/${patientId}?hospital_id=${hospitalId}`,
    'PUT',
    patientData
  )
}

export const deletePatient = (
  patientId,
  hospitalId = 1
) => {
  return sendAPIRequest(
    `/api/patients/${patientId}?hospital_id=${hospitalId}`,
    'DELETE'
  )
}

// ================= DOCTORS API =================

// Fetch all doctors
export const getDoctors = (hospitalId = 1) => {
  return fetchAPI(
    `/api/doctors/?hospital_id=${hospitalId}`
  )
}

// Fetch a single doctor
export const getDoctorById = (
  doctorId,
  hospitalId = 1
) => {
  return fetchAPI(
    `/api/doctors/${doctorId}?hospital_id=${hospitalId}`
  )
}

// Fetch departments for Add Doctor dropdown
export const getDoctorDepartments = (
  hospitalId = 1
) => {
  return fetchAPI(
    `/api/doctors/departments?hospital_id=${hospitalId}`
  )
}

// Create a new doctor and user account
export const createDoctor = (
  doctorData,
  hospitalId = 1
) => {
  return sendAPIRequest(
    `/api/doctors/?hospital_id=${hospitalId}`,
    'POST',
    doctorData
  )
}

// Update doctor professional details
export const updateDoctor = (
  doctorId,
  doctorData,
  hospitalId = 1
) => {
  return sendAPIRequest(
    `/api/doctors/${doctorId}?hospital_id=${hospitalId}`,
    'PUT',
    doctorData
  )
}

// Delete doctor record
export const deleteDoctor = (
  doctorId,
  hospitalId = 1
) => {
  return sendAPIRequest(
    `/api/doctors/${doctorId}?hospital_id=${hospitalId}`,
    'DELETE'
  )
}

// ================= DATABASE EXPLORER API =================

export const getDatabaseHealth = () => {
  return fetchAPI('/api/database/health')
}

export const getDatabaseInfo = () => {
  return fetchAPI('/api/database/info')
}

export const getDatabaseTables = (hospitalId = 1) => {
  return fetchAPI(
    `/api/database/tables?hospital_id=${hospitalId}`
  )
}

export const getTableData = (
  tableName,
  hospitalId = 1
) => {
  return fetchAPI(
    `/api/database/table/${tableName}?hospital_id=${hospitalId}`
  )
}

// ================= OS MONITORING API =================

export const getOSMetrics = () => {
  return fetchAPI('/api/os/metrics')
}

export const getOSHistory = (limit = 20) => {
  return fetchAPI(`/api/os/history?limit=${limit}`)
}

export const getOSProcesses = (limit = 50) => {
  return fetchAPI(`/api/os/processes?limit=${limit}`)
}

// ================= FEDERATED LEARNING API =================

export const getFederatedSummary = (limit = 10) => {
  return fetchAPI(`/api/federated/summary?limit=${limit}`)
}

export const runFederatedRound = () => {
  return sendAPIRequest('/api/federated/run', 'POST')
}

// ================= AUDIT LOG API =================

export const getAuditLogs = (limit = 100) => {
  return fetchAPI(`/api/audit-logs?limit=${limit}`)
}
// ================= APPOINTMENTS API =================

// Fetch all appointments
export const getAppointments = (hospitalId = 1) => {
  return fetchAPI(
    `/api/appointments/?hospital_id=${hospitalId}`
  )
}

// Fetch a single appointment
export const getAppointmentById = (
  appointmentId,
  hospitalId = 1
) => {
  return fetchAPI(
    `/api/appointments/${appointmentId}?hospital_id=${hospitalId}`
  )
}

// Create a new appointment
export const createAppointment = (
  appointmentData,
  hospitalId = 1
) => {
  return sendAPIRequest(
    `/api/appointments/?hospital_id=${hospitalId}`,
    'POST',
    appointmentData
  )
}

// Update an appointment
export const updateAppointment = (
  appointmentId,
  appointmentData,
  hospitalId = 1
) => {
  return sendAPIRequest(
    `/api/appointments/${appointmentId}?hospital_id=${hospitalId}`,
    'PUT',
    appointmentData
  )
}

// Delete an appointment
export const deleteAppointment = (
  appointmentId,
  hospitalId = 1
) => {
  return sendAPIRequest(
    `/api/appointments/${appointmentId}?hospital_id=${hospitalId}`,
    'DELETE'
  )
}
// ================= MEDICAL RECORDS API =================

export const getMedicalRecords = (hospitalId = 1) => {
  return fetchAPI(
    `/api/medical-records/?hospital_id=${hospitalId}`
  )
}

export const getMedicalRecordById = (
  recordId,
  hospitalId = 1
) => {
  return fetchAPI(
    `/api/medical-records/${recordId}?hospital_id=${hospitalId}`
  )
}

export const createMedicalRecord = (
  recordData,
  hospitalId = 1
) => {
  return sendAPIRequest(
    `/api/medical-records/?hospital_id=${hospitalId}`,
    "POST",
    recordData
  )
}

export const updateMedicalRecord = (
  recordId,
  recordData,
  hospitalId = 1
) => {
  return sendAPIRequest(
    `/api/medical-records/${recordId}?hospital_id=${hospitalId}`,
    "PUT",
    recordData
  )
}

export const deleteMedicalRecord = (
  recordId,
  hospitalId = 1
) => {
  return sendAPIRequest(
    `/api/medical-records/${recordId}?hospital_id=${hospitalId}`,
    "DELETE"
  )
}
// ================= PRESCRIPTIONS API =================

// Fetch all prescriptions
export const getPrescriptions = (hospitalId = 1) => {
  return fetchAPI(
    `/api/prescriptions/?hospital_id=${hospitalId}`
  )
}

// Fetch a single prescription
export const getPrescriptionById = (
  prescriptionId,
  hospitalId = 1
) => {
  return fetchAPI(
    `/api/prescriptions/${prescriptionId}?hospital_id=${hospitalId}`
  )
}

// Create a prescription
export const createPrescription = (
  prescriptionData,
  hospitalId = 1
) => {
  return sendAPIRequest(
    `/api/prescriptions/?hospital_id=${hospitalId}`,
    'POST',
    prescriptionData
  )
}

// Update a prescription
export const updatePrescription = (
  prescriptionId,
  prescriptionData,
  hospitalId = 1
) => {
  return sendAPIRequest(
    `/api/prescriptions/${prescriptionId}?hospital_id=${hospitalId}`,
    'PUT',
    prescriptionData
  )
}

// Delete a prescription
export const deletePrescription = (
  prescriptionId,
  hospitalId = 1
) => {
  return sendAPIRequest(
    `/api/prescriptions/${prescriptionId}?hospital_id=${hospitalId}`,
    'DELETE'
  )
}
// ================= LAB ORDERS API =================

export const getLabOrders = (hospitalId = 1) => {
  return fetchAPI(
    `/api/lab-orders/?hospital_id=${hospitalId}`
  )
}

export const getLabOrderById = (
  labOrderId,
  hospitalId = 1
) => {
  return fetchAPI(
    `/api/lab-orders/${labOrderId}?hospital_id=${hospitalId}`
  )
}

export const createLabOrder = (
  labOrderData,
  hospitalId = 1
) => {
  return sendAPIRequest(
    `/api/lab-orders/?hospital_id=${hospitalId}`,
    'POST',
    labOrderData
  )
}

export const updateLabOrder = (
  labOrderId,
  labOrderData,
  hospitalId = 1
) => {
  return sendAPIRequest(
    `/api/lab-orders/${labOrderId}?hospital_id=${hospitalId}`,
    'PUT',
    labOrderData
  )
}

export const deleteLabOrder = (
  labOrderId,
  hospitalId = 1
) => {
  return sendAPIRequest(
    `/api/lab-orders/${labOrderId}?hospital_id=${hospitalId}`,
    'DELETE'
  )
}