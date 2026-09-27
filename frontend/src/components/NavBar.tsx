import { useEffect, useState } from 'react'
import { Link, NavLink, useNavigate } from 'react-router-dom'
import { useAuth } from '../useAuth.ts'

const MAIN_LINKS = [
  { to: '/', label: 'Home', end: true },
  { to: '/products', label: 'Products', end: false },
  { to: '/about', label: 'About Us', end: false },
]

// Rotates through the store's real promises, one at a time.
const ANNOUNCEMENTS = [
  'Officially licensed Yale apparel',
  'Made to order at 57 Broadway, New Haven',
  'Most orders printed in 5–8 business days',
  '30-day returns on unworn pieces',
]
const ROTATE_MS = 4500

export function Crest({ className = '' }: { className?: string }) {
  return (
    <svg className={className} viewBox="0 0 64 64" aria-hidden="true">
      <path d="M8 4h48v28c0 15-11 23-24 29C19 55 8 47 8 32z" fill="currentColor" />
      <path
        d="M13 9h38v23c0 12-8.5 18.5-19 23.5C21.5 50.5 13 44 13 32z"
        fill="none"
        stroke="var(--cream)"
        strokeWidth="2"
      />
      <text x="32" y="40" fontFamily="Fraunces, Georgia, serif" fontSize="22" fontWeight="700" fill="var(--cream)" textAnchor="middle">
        CC
      </text>
    </svg>
  )
}

export default function NavBar() {
  const [notice, setNotice] = useState(0)
  useEffect(() => {
    const id = setInterval(() => setNotice((n) => (n + 1) % ANNOUNCEMENTS.length), ROTATE_MS)
    return () => clearInterval(id)
  }, [])

  const [open, setOpen] = useState(false)
  const close = () => setOpen(false)
  const { user, loading, logout } = useAuth()
  const navigate = useNavigate()

  async function handleLogout() {
    close()
    // Leave the page first so account-only pages don't redirect to /login.
    navigate('/')
    await logout()
  }

  return (
    <header className="site-header">
      <div className="announcement" aria-live="off">
        <span key={notice} className="announcement-text">
          <span className="announcement-star" aria-hidden="true">✦</span> {ANNOUNCEMENTS[notice]}
        </span>
      </div>
      <nav className="nav container" aria-label="Main">
        <Link to="/" className="brand" onClick={close}>
          <Crest className="brand-mark" />
          <span className="brand-text">
            <span className="brand-name">Campus Customs</span>
            <span className="brand-sub">Yale Bulldog Blue</span>
          </span>
        </Link>

        <button
          className="nav-toggle"
          aria-expanded={open}
          aria-controls="nav-links"
          onClick={() => setOpen((o) => !o)}
        >
          <span className="sr-only">Menu</span>☰
        </button>

        <div id="nav-links" className={`nav-links ${open ? 'is-open' : ''}`}>
          <ul className="nav-main">
            {MAIN_LINKS.map((link) => (
              <li key={link.to}>
                <NavLink to={link.to} end={link.end} onClick={close}>
                  {link.label}
                </NavLink>
              </li>
            ))}
          </ul>
          <ul className="nav-account">
            {loading ? null : user ? (
              <>
                <li>
                  <NavLink to="/account" onClick={close} className="nav-user">
                    <span className="nav-avatar" aria-hidden="true">{user.first_name[0]}</span>
                    Hi, {user.first_name}
                  </NavLink>
                </li>
                <li>
                  <button className="btn btn-small btn-secondary" onClick={handleLogout}>
                    Log out
                  </button>
                </li>
              </>
            ) : (
              <>
                <li>
                  <NavLink to="/login" onClick={close}>
                    Log in
                  </NavLink>
                </li>
                <li>
                  <NavLink to="/signup" className="btn btn-small" onClick={close}>
                    Create account
                  </NavLink>
                </li>
              </>
            )}
          </ul>
        </div>
      </nav>
    </header>
  )
}
