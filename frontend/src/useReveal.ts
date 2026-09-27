import { useEffect } from 'react'
import { useLocation } from 'react-router-dom'

// Fades elements with class "reveal" in as they scroll into view. New ones
// (a page change, products arriving from the API) are picked up automatically.
export function useReveal() {
  const { pathname, search } = useLocation()

  useEffect(() => {
    if (!('IntersectionObserver' in window) || matchMedia('(prefers-reduced-motion: reduce)').matches) {
      document.querySelectorAll('.reveal').forEach((el) => el.classList.add('is-visible'))
      return
    }
    const io = new IntersectionObserver(
      (entries) => {
        for (const entry of entries) {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible')
            io.unobserve(entry.target)
          }
        }
      },
      { rootMargin: '0px 0px -8% 0px' },
    )
    const watch = () => document.querySelectorAll('.reveal:not(.is-visible)').forEach((el) => io.observe(el))
    watch()
    const mo = new MutationObserver(watch)
    mo.observe(document.body, { childList: true, subtree: true })
    return () => {
      io.disconnect()
      mo.disconnect()
    }
  }, [pathname, search])
}
