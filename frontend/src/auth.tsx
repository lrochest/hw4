import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { createAccount, fetchCurrentUser, logIn, logOut, type User } from './api.ts'
import { AuthContext } from './useAuth.ts'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetchCurrentUser()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const u = await logIn(email, password)
    setUser(u)
    return u
  }, [])

  const signup = useCallback(async (firstName: string, lastName: string, email: string, password: string) => {
    const u = await createAccount(firstName, lastName, email, password)
    setUser(u)
    return u
  }, [])

  const logout = useCallback(async () => {
    await logOut().catch(() => undefined)
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, loading, login, signup, logout }}>{children}</AuthContext.Provider>
  )
}
