import {
  BrowserRouter,
  Routes,
  Route,
  Navigate
} from 'react-router-dom'

import Sidebar from './components/Sidebar'

import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Patients from './pages/Patients'
import Doctors from './pages/Doctors'
import Appointments from './pages/Appointments'
import MedicalRecords from './pages/MedicalRecords'
import Prescriptions from './pages/Prescriptions'
import LabOrders from './pages/LabOrders'
import FederatedLearning from './pages/FederatedLearning'
import Hospitals from './pages/Hospitals'
import OSMonitoring from './pages/OSMonitoring'
import DatabaseExplorer from './pages/DatabaseExplorer'
import Reports from './pages/Reports'
import Settings from './pages/Settings'

import { getToken } from './services/api'


// ================= PROTECTED ROUTE =================

function ProtectedRoute({ children }) {
  const token = getToken()

  if (!token) {
    return <Navigate to="/login" replace />
  }

  return children
}


// ================= APP LAYOUT =================

function AppLayout({ children }) {
  return (
    <div className="app-layout">

      <Sidebar />

      <div className="main-area">
        <div className="page-content">
          {children}
        </div>
      </div>

    </div>
  )
}


// ================= PROTECTED PAGE =================

function ProtectedPage({ children }) {
  return (
    <ProtectedRoute>
      <AppLayout>
        {children}
      </AppLayout>
    </ProtectedRoute>
  )
}


// ================= MAIN APP =================

function App() {
  return (
    <BrowserRouter>

      <Routes>

        {/* Login */}
        <Route
          path="/login"
          element={<Login />}
        />

        {/* Dashboard */}
        <Route
          path="/"
          element={
            <ProtectedPage>
              <Dashboard />
            </ProtectedPage>
          }
        />

        {/* Patients */}
        <Route
          path="/patients"
          element={
            <ProtectedPage>
              <Patients />
            </ProtectedPage>
          }
        />

        {/* Doctors */}
        <Route
          path="/doctors"
          element={
            <ProtectedPage>
              <Doctors />
            </ProtectedPage>
          }
        />

        {/* Appointments */}
        <Route
          path="/appointments"
          element={
            <ProtectedPage>
              <Appointments />
            </ProtectedPage>
          }
        />

        {/* Medical Records */}
        <Route
          path="/medical-records"
          element={
            <ProtectedPage>
              <MedicalRecords />
            </ProtectedPage>
          }
        />

        {/* Prescriptions */}
        <Route
          path="/prescriptions"
          element={
            <ProtectedPage>
              <Prescriptions />
            </ProtectedPage>
          }
        />

        {/* Lab Orders */}
        <Route
          path="/lab-orders"
          element={
            <ProtectedPage>
              <LabOrders />
            </ProtectedPage>
          }
        />

        {/* Federated Learning */}
        <Route
          path="/federated-learning"
          element={
            <ProtectedPage>
              <FederatedLearning />
            </ProtectedPage>
          }
        />

        {/* Hospitals */}
        <Route
          path="/hospitals"
          element={
            <ProtectedPage>
              <Hospitals />
            </ProtectedPage>
          }
        />

        {/* OS Monitoring */}
        <Route
          path="/os-monitoring"
          element={
            <ProtectedPage>
              <OSMonitoring />
            </ProtectedPage>
          }
        />

        {/* Database Explorer */}
        <Route
          path="/database-explorer"
          element={
            <ProtectedPage>
              <DatabaseExplorer />
            </ProtectedPage>
          }
        />

        {/* Reports */}
        <Route
          path="/reports"
          element={
            <ProtectedPage>
              <Reports />
            </ProtectedPage>
          }
        />

        {/* Settings */}
        <Route
          path="/settings"
          element={
            <ProtectedPage>
              <Settings />
            </ProtectedPage>
          }
        />

        {/* Unknown routes */}
        <Route
          path="*"
          element={<Navigate to="/" replace />}
        />

      </Routes>

    </BrowserRouter>
  )
}

export default App