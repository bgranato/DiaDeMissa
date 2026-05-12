import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { getUsuarioAtual, getToken, logout as logoutService } from '../services/auth'
import type { Usuario } from '../types/usuario'

interface AuthContextData {
  usuario: Usuario | null
  estaCarregando: boolean
  estaAutenticado: boolean
  setUsuario: (u: Usuario) => void
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextData>({
  usuario: null,
  estaCarregando: true,
  estaAutenticado: false,
  setUsuario: () => {},
  logout: async () => {},
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [estaCarregando, setEstaCarregando] = useState(true)

  useEffect(() => {
    carregarUsuario()
  }, [])

  async function carregarUsuario() {
    try {
      const token = await getToken()
      if (token) {
        const user = await getUsuarioAtual()
        setUsuario(user)
      }
    } catch {
      await logoutService()
    } finally {
      setEstaCarregando(false)
    }
  }

  const logout = useCallback(async () => {
    await logoutService()
    setUsuario(null)
  }, [])

  return (
    <AuthContext.Provider
      value={{
        usuario,
        estaCarregando,
        estaAutenticado: !!usuario,
        setUsuario,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
