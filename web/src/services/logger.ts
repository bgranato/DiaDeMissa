import api from './api'

export function log(tipo: 'navigation' | 'error' | 'action', mensagem: string, dados?: any) {
  api.post('/logs', { tipo, mensagem, dados }).catch(() => {})
}

export function logNav(from: string, to: string) {
  log('navigation', `Navegou: ${from} → ${to}`, { from, to })
}

export function logError(contexto: string, erro: any) {
  log('error', `Erro em ${contexto}`, {
    message: erro?.message || String(erro),
    status: erro?.response?.status,
    data: erro?.response?.data,
  })
}
