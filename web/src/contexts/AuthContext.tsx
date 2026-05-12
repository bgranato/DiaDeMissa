import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from 'react'
import { getUsuarioAtual, getToken, logout as logoutService } from '../services/auth'
import type { Usuario } from '../types/usuario'

interface AuthContextData {
  usuario: Usuario | null
  estaCarregando: boolean
  estaAutenticado: boolean
  setUsuario: (u: Usuario) => void
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextData>({} as AuthContextData)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [estaCarregando, setEstaCarregando] = useState(true)

  useEffect(() => {
    const token = getToken()
    if (token) {
      getUsuarioAtual()
        .then(setUsuario)
        .catch(() => localStorage.removeItem('@missa_hoje_token'))
        .finally(() => setEstaCarregando(false))
    } else {
      setEstaCarregando(false)
    }
  }, [])

  const logout = useCallback(async () => {
    await logoutService()
    setUsuario(null)
  }, [])

  return (
    <AuthContext.Provider value={{ usuario, estaCarregando, estaAutenticado: !!usuario, setUsuario, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
