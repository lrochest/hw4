import { createContext, useContext } from 'react'
import type { PageResults } from './api.ts'

// Products the chat has put on the page. Written by ChatWidget, read by the
// Products page (at /products?view=chat).

export interface ShownResults extends PageResults {
  // Changes every time new results arrive, so the page can scroll back to the top.
  id: number
}

export interface ChatResultsState {
  results: ShownResults | null
  show: (results: PageResults) => void
  clear: () => void
}

export const CHAT_VIEW = 'chat'

export const ChatResultsContext = createContext<ChatResultsState | null>(null)

export function useChatResults(): ChatResultsState {
  const ctx = useContext(ChatResultsContext)
  if (!ctx) throw new Error('useChatResults must be used inside <ChatResultsProvider>')
  return ctx
}
