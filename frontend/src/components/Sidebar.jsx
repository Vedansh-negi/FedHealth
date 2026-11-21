import { NavLink, useNavigate } from 'react-router-dom'

import { getSavedUser, logoutUser } from '../services/api'


function Sidebar() {
  const navigate = useNavigate()
  const user = getSavedUser()
  const role = user?.role

  const menuItems = [
    {
      name: 'Dashboard',
      path: '/',
      icon: '📊'
    },
    {
      name: 'Patients',
      path: '/patients',
      icon: '👥'
    },
    {
      name: 'Doctors',
      path: '/doctors',
      icon: '👨‍⚕️'
    },
    {
      name: 'Appointments',
      path: '/appointments',
      icon: '📅'
    },
    {
      name: 'Medical Records',
      path: '/medical-records',
      roles: ['admin', 'doctor', 'nurse'],
      icon: '📋'
    },
    {
      name: 'Prescriptions',
      path: '/prescriptions',
      roles: ['admin', 'doctor', 'nurse'],
      icon: '💊'
    },
    {
      name: 'Lab Orders',
      path: '/lab-orders',
      roles: ['admin', 'doctor', 'nurse', 'lab_technician'],
      icon: '🧪'
    },
    {
      name: 'Federated Learning',
      path: '/federated-learning',
      roles: ['admin', 'doctor'],
      icon: '🧠'
    },
    {
      name: 'Hospitals',
      path: '/hospitals',
      icon: '🏥'
    },
    {
      name: 'OS Monitoring',
      path: '/os-monitoring',
      roles: ['admin'],
      icon: '⚙️'
    },
    {
      name: 'Database Explorer',
      path: '/database-explorer',
      roles: ['admin'],
      icon: '🗄️'
    },
    {
      name: 'Reports',
      path: '/reports',
      icon: '📈'
    },
    {
      name: 'Settings',
      path: '/settings',
      roles: ['admin'],
      icon: '🔧'
    }
  ]


  // Logout
  const handleLogout = () => {
    logoutUser()

    navigate('/login', {
      replace: true
    })
  }


  return (
    <aside className="sidebar">

      {/* Brand */}
      <div className="sidebar-brand">

        <div className="sidebar-brand-icon">
          🏥
        </div>

        <div>
          <h2>FedHealth</h2>
          <span>Healthcare Platform</span>
        </div>

      </div>


      {/* Navigation title */}
      <div className="sidebar-section-title">
        MAIN MENU
      </div>


      {/* Navigation links */}
      <nav className="sidebar-nav">

        {menuItems
          .filter((item) => !item.roles || item.roles.includes(role))
          .map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              isActive
                ? 'sidebar-link active'
                : 'sidebar-link'
            }
          >

            <span className="sidebar-link-icon">
              {item.icon}
            </span>

            <span className="sidebar-link-text">
              {item.name}
            </span>

          </NavLink>
        ))}

      </nav>


      {/* Sidebar bottom */}
      <div className="sidebar-bottom">

        <div className="sidebar-user-info">

          <div className="sidebar-user-avatar">
            👤
          </div>

          <div className="sidebar-user-details">
            <strong>{user?.full_name || 'FedHealth User'}</strong>
            <span>
              {role ? role.replace('_', ' ') : 'Staff'}
              {user?.hospital_id ? ` · Hospital ${user.hospital_id}` : ''}
            </span>
          </div>

        </div>


        {/* Logout */}
        <button
          type="button"
          className="sidebar-link logout-link"
          onClick={handleLogout}
        >

          <span className="sidebar-link-icon">
            🚪
          </span>

          <span className="sidebar-link-text">
            Logout
          </span>

        </button>

      </div>

    </aside>
  )
}

export default Sidebar