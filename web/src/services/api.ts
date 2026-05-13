import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'
const TOKEN_KEY = '@missa_hoje_token'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    // Só limpa o token se for um 401 NO endpoint exato que valida a sessão.
    // /usuarios/me/historico e /usuarios/me/preferencias são outros endpoints
    // — um 401 deles NÃO significa que o token está inválido (pode ser regra
    // de negócio ou rate limit), então não derrubamos a sessão.
    const url = err.config?.url || ''
    const isSessionCheck = url.endsWith('/usuarios/me') || url === '/usuarios/me'
    if (err.response?.status === 401 && isSessionCheck) {
      localStorage.removeItem(TOKEN_KEY)
    }
    return Promise.reject(err)
  },
)

export { TOKEN_KEY }
export default api
