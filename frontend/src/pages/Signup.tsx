import { useState, type FormEvent } from 'react'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import { useAuth } from '../useAuth.ts'

const MIN_PASSWORD = 8

export default function Signup() {
  const { user, signup } = useAuth()
  const navigate = useNavigate()

  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  // Set once this form succeeds, so the "already logged in" redirect below
  // doesn't override the navigation the submit handler makes.
  const [submitted, setSubmitted] = useState(false)

  if (user && !submitted) return <Navigate to="/account" replace />

  const mismatch = confirm.length > 0 && confirm !== password

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError(null)
    if (password.length < MIN_PASSWORD) {
      setError(`Please use at least ${MIN_PASSWORD} characters for your password.`)
      return
    }
    if (password !== confirm) {
      setError('The two passwords don’t match.')
      return
    }
    setBusy(true)
    try {
      setSubmitted(true)
      await signup(firstName.trim(), lastName.trim(), email.trim(), password)
      navigate('/account', { replace: true, state: { welcome: true } })
    } catch (err) {
      setSubmitted(false)
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="page container auth">
      <form className="auth-card" onSubmit={handleSubmit}>
        <h1>Create account</h1>
        <p className="muted">Save your conversations and pick up where you left off.</p>

        <div className="field-row">
          <label>
            First name
            <input autoComplete="given-name" required value={firstName} onChange={(e) => setFirstName(e.target.value)} />
          </label>
          <label>
            Last name
            <input autoComplete="family-name" required value={lastName} onChange={(e) => setLastName(e.target.value)} />
          </label>
        </div>
        <label>
          Email
          <input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Password
          <input
            type="password"
            autoComplete="new-password"
            required
            minLength={MIN_PASSWORD}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            aria-describedby="password-hint"
          />
          <span id="password-hint" className="field-hint">At least {MIN_PASSWORD} characters.</span>
        </label>
        <label>
          Confirm password
          <input
            type="password"
            autoComplete="new-password"
            required
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            aria-invalid={mismatch}
          />
          {mismatch && <span className="field-hint field-hint-error">Passwords don’t match yet.</span>}
        </label>

        {error && (
          <p className="notice notice-error" role="alert">
            {error}
          </p>
        )}

        <button type="submit" className="btn btn-block" disabled={busy}>
          {busy ? 'Creating account…' : 'Create account'}
        </button>
        <p className="muted small">
          Already have an account? <Link to="/login">Log in</Link>
        </p>
      </form>
    </div>
  )
}
