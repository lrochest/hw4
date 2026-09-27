import { useState, type ReactNode } from 'react'
import { PageContext, type PageReport } from './usePageContext.ts'

export function PageContextProvider({ children }: { children: ReactNode }) {
  const [report, setReport] = useState<PageReport>({})
  return <PageContext.Provider value={{ report, setReport }}>{children}</PageContext.Provider>
}
