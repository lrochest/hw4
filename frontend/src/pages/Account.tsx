import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../useAuth.ts'

export default function Account() {
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const welcome = (location.state as { welcome?: boolean } | null)?.welcome

  if (loading) return <div className="page container muted">Loading…</div>
  if (!user) return <Navigate to="/login" replace state={{ from: '/account' }} />

  async function handleLogout() {
    // Leave the page first so this page doesn't redirect to /login.
    navigate('/', { replace: true })
    await logout()
  }

  return (
    <div className="page container auth">
      <div className="auth-card">
        <p className="eyebrow">{welcome ? 'Account created' : 'Your account'}</p>
        <h1>{welcome ? `Welcome, ${user.first_name}!` : `Hi, ${user.first_name}`}</h1>
        <dl className="account-details">
          <dt>Name</dt>
          <dd>
            {user.first_name} {user.last_name}
          </dd>
          <dt>Email</dt>
          <dd>{user.email}</dd>
        </dl>
        <Link to="/products" className="btn btn-block">
          Start shopping
        </Link>
        <button className="btn btn-block btn-secondary" onClick={handleLogout}>
          Log out
        </button>
      </div>
    </div>
  )
}
