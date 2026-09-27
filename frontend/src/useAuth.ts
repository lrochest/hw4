import { createContext, useContext } from 'react'
import type { User } from './api.ts'

export interface AuthState {
  user: User | null
  // True until the first /api/auth/me check finishes, so pages don't flash "logged out".
  loading: boolean
  login: (email: string, password: string) => Promise<User>
  signup: (firstName: string, lastName: string, email: string, password: string) => Promise<User>
  logout: () => Promise<void>
}

export const AuthContext = createContext<AuthState | null>(null)

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used inside <AuthProvider>')
  return ctx
}
