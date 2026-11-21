import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { loginUser } from '../services/api'

function Login() {
  const navigate = useNavigate()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [hospitalId, setHospitalId] = useState('1')

  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleLogin(event) {
    event.preventDefault()

    setError('')
    setLoading(true)

    try {
      await loginUser(
        email,
        password,
        Number(hospitalId)
      )

      navigate('/', { replace: true })
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-page">
      <div className="login-card">

        <div className="login-header">
          <h1>FedHealth</h1>
          <p>Hospital Management & Federated Healthcare</p>
        </div>

        <h2>Welcome Back</h2>
        <p className="login-subtitle">
          Login to your hospital account
        </p>

        <form onSubmit={handleLogin}>

          <label htmlFor="email">
            Email Address
          </label>

          <input
            id="email"
            type="email"
            placeholder="Enter your email"
            value={email}
            onChange={(event) =>
              setEmail(event.target.value)
            }
            required
          />

          <label htmlFor="password">
            Password
          </label>

          <input
            id="password"
            type="password"
            placeholder="Enter your password"
            value={password}
            onChange={(event) =>
              setPassword(event.target.value)
            }
            required
          />

          <label htmlFor="hospital">
            Hospital
          </label>

          <select
            id="hospital"
            value={hospitalId}
            onChange={(event) =>
              setHospitalId(event.target.value)
            }
          >
            <option value="1">Hospital 1</option>
            <option value="2">Hospital 2</option>
            <option value="3">Hospital 3</option>
          </select>

          {error && (
            <div className="login-error">
              {error}
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
          >
            {loading ? 'Logging in...' : 'Login'}
          </button>

        </form>

        <div className="login-footer">
          FedHealth © 2026
        </div>

      </div>
    </div>
  )
}

export default Login