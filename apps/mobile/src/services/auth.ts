import AsyncStorage from '@react-native-async-storage/async-storage'
import api, { TOKEN_KEY } from './api'
import type { LoginResponse, Usuario } from '../types/usuario'

export async function login(email: string, senha: string): Promise<LoginResponse> {
  const response = await api.post<LoginResponse>('/auth/login', { email, senha })
  await AsyncStorage.setItem(TOKEN_KEY, response.data.access_token)
  return response.data
}

export async function cadastrar(nome: string, email: string, senha: string): Promise<Usuario> {
  const response = await api.post<Usuario>('/usuarios', { nome, email, senha })
  return response.data
}

export async function loginGoogle(token: string): Promise<LoginResponse> {
  const response = await api.post<LoginResponse>('/auth/google', { token })
  await AsyncStorage.setItem(TOKEN_KEY, response.data.access_token)
  return response.data
}

export async function getUsuarioAtual(): Promise<Usuario> {
  const response = await api.get<Usuario>('/usuarios/me')
  return response.data
}

export async function atualizarUsuario(dados: Partial<Usuario>): Promise<Usuario> {
  const response = await api.put<Usuario>('/usuarios/me', dados)
  return response.data
}

export async function logout(): Promise<void> {
  await AsyncStorage.removeItem(TOKEN_KEY)
}

export async function getToken(): Promise<string | null> {
  return AsyncStorage.getItem(TOKEN_KEY)
}
