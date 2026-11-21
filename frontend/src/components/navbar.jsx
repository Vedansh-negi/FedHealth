
import { Search, Bell, CircleHelp } from 'lucide-react'

function Navbar() {
  return (
    <header className="top-navbar">
      <div>
        <p className="eyebrow">FEDHEALTH PLATFORM</p>
        <h2>Healthcare Intelligence</h2>
      </div>

      <div className="navbar-actions">
        <label className="search-box">
          <Search size={17} />
          <input placeholder="Search dashboard..." />
        </label>

        <button className="icon-button" aria-label="Help">
          <CircleHelp size={19} />
        </button>

        <button className="icon-button" aria-label="Notifications">
          <Bell size={19} />
        </button>

        <div className="avatar">FH</div>
      </div>
    </header>
  )
}

export default Navbar
