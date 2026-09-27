import { Link } from 'react-router-dom'

export default function NotFound() {
  return (
    <div className="page container">
      <h1>Page not found</h1>
      <p className="muted">That page wandered off. Let's get you back to the shop.</p>
      <Link to="/products" className="btn">Browse products</Link>
    </div>
  )
}
