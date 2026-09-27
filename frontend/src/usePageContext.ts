import { createContext, useContext, useEffect } from 'react'

// What the current page shows, so the chat can tell the agent what "this" or
// "these" means. Pages report it with useReportPage(); ChatWidget reads it.

export interface PageReport {
  productId?: string | null // the product on a /products/<id> page
  visibleProductIds?: string[] // product cards on screen, in order
  visibleTotal?: number
  label?: string | null // e.g. "Chat results: Hoodies", "Category: Crewnecks"
}

export interface PageContextState {
  report: PageReport
  setReport: (report: PageReport) => void
}

export const PageContext = createContext<PageContextState | null>(null)

export function usePageContext(): PageContextState {
  const ctx = useContext(PageContext)
  if (!ctx) throw new Error('usePageContext must be used inside <PageContextProvider>')
  return ctx
}

// Report while mounted; cleared when the page unmounts. The key keeps the
// effect from re-running on every render when the report hasn't changed.
export function useReportPage(report: PageReport) {
  const { setReport } = usePageContext()
  const key = JSON.stringify(report)
  useEffect(() => {
    setReport(JSON.parse(key) as PageReport)
    return () => setReport({})
  }, [key, setReport])
}
