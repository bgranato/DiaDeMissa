import api, { TOKEN_KEY } from './api'
import type { LoginResponse, Usuario } from '../types/usuario'

export async function login(email: string, senha: string): Promise<LoginResponse> {
  const res = await api.post<LoginResponse>('/auth/login', { email, senha })
  localStorage.setItem(TOKEN_KEY, res.data.access_token)
  return res.data
}

export async function cadastrar(
  nome: string,
  email: string,
  senha: string,
  celular?: string,
  igreja?: string,
): Promise<Usuario> {
  const res = await api.post<Usuario>('/usuarios', { nome, email, senha, celular, igreja })
  return res.data
}

export async function recuperarSenha(email: string): Promise<void> {
  await api.post('/auth/recuperar-senha', { email })
}

export async function redefinirSenha(token: string, nova_senha: string): Promise<void> {
  await api.post('/auth/redefinir-senha', { token, nova_senha })
}

export async function alterarSenha(senha_atual: string, nova_senha: string): Promise<void> {
  await api.post('/usuarios/me/alterar-senha', { senha_atual, nova_senha })
}

export async function loginGoogle(token: string): Promise<LoginResponse> {
  const res = await api.post<LoginResponse>('/auth/google', { token })
  localStorage.setItem(TOKEN_KEY, res.data.access_token)
  return res.data
}

// Login com Google via token de acesso (botão próprio, fluxo OAuth token).
export async function loginGoogleToken(access_token: string): Promise<LoginResponse> {
  const res = await api.post<LoginResponse>('/auth/google-token', { access_token })
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
