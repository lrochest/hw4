import { useCallback, useState, type ReactNode } from 'react'
import type { PageResults } from './api.ts'
import { ChatResultsContext, type ShownResults } from './useChatResults.ts'

// Kept in sessionStorage so a reload, or coming back from a product page,
// still shows the same results.
const STORAGE_KEY = 'cc-chat-results'

function load(): ShownResults | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as ShownResults) : null
  } catch {
    return null
  }
}

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<ShownResults | null>(load)

  const show = useCallback((page: PageResults) => {
    const next = { ...page, id: Date.now() }
    setResults(next)
    try {
      sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    } catch {
      // Storage full or disabled: results still show until the next reload.
    }
  }, [])

  const clear = useCallback(() => {
    setResults(null)
    sessionStorage.removeItem(STORAGE_KEY)
  }, [])

  return <ChatResultsContext.Provider value={{ results, show, clear }}>{children}</ChatResultsContext.Provider>
}
