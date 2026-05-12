import api, { TOKEN_KEY } from './api'
import type { LoginResponse, Usuario } from '../types/usuario'

export async function login(email: string, senha: string): Promise<LoginResponse> {
  const res = await api.post<LoginResponse>('/auth/login', { email, senha })
  localStorage.setItem(TOKEN_KEY, res.data.access_token)
  return res.data
}

export async function cadastrar(nome: string, email: string, senha: string): Promise<Usuario> {
  const res = await api.post<Usuario>('/usuarios', { nome, email, senha })
  return res.data
}

export async function loginGoogle(token: string): Promise<LoginResponse> {
  const res = await api.post<LoginResponse>('/auth/google', { token })
  localStorage.setItem(TOKEN_KEY, res.data.access_token)
  return res.data
}

export async function getUsuarioAtual(): Promise<Usuario> {
  const res = await api.get<Usuario>('/usuarios/me')
  return res.data
}

export async function atualizarUsuario(dados: Partial<Usuario>): Promise<Usuario> {
  const res = await api.put<Usuario>('/usuarios/me', dados)
  return res.data
}

export async function logout(): Promise<void> {
  localStorage.removeItem(TOKEN_KEY)
}

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}
