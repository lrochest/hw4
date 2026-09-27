import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

// React Router keeps the scroll position between pages; start each new page
// at the top unless the link points to a section (#returns, #orders).
export default function ScrollToTop() {
  const { pathname, hash } = useLocation()

  useEffect(() => {
    if (hash) {
      document.getElementById(hash.slice(1))?.scrollIntoView()
    } else {
      window.scrollTo(0, 0)
    }
  }, [pathname, hash])

  return null
}
