import axios, { AxiosInstance } from 'axios'
import AsyncStorage from '@react-native-async-storage/async-storage'

// Base da API. Default = PRODUÇÃO. Para desenvolvimento (apontar pro backend local),
// sobrescreva com a env do Expo EXPO_PUBLIC_API_URL, ex. num .env:
//   EXPO_PUBLIC_API_URL=http://localhost:8000/api/v1
// (o Expo injeta automaticamente vars com prefixo EXPO_PUBLIC_ em process.env.)
const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL || 'https://diademissa.com.br/api/v1'
const TOKEN_KEY = '@missa_hoje_token'

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use(async (config) => {
  const token = await AsyncStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export { TOKEN_KEY }

export default api
