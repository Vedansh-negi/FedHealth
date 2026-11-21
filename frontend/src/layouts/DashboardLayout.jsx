
import Sidebar from '../components/Sidebar'
import Navbar from '../components/navbar'

function DashboardLayout({ children }) {
  return (
    <div className="app-layout">
      <Sidebar />

      <div className="main-area">
        <Navbar />
        <main className="page-content">{children}</main>
      </div>
    </div>
  )
}

export default DashboardLayout
