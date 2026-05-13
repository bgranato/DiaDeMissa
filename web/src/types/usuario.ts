export interface Usuario {
  id: number
  nome: string
  email: string
  celular?: string | null
  igreja?: string | null
  is_admin?: boolean
  provider: string
  data_criacao: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  usuario: Usuario
}

export interface Preferencias {
  tamanho_fonte: number
  modo_escuro: boolean
  alto_contraste: boolean
  leitura_simplificada: boolean
  notificacoes_ativas: boolean
}

export type HistoricoStatus = 'concluida' | 'em_progresso' | 'nao_acompanhada'

export interface HistoricoEntry {
  missa_id: number
  data: string
  celebracao: string | null
  ultimo_bloco_id: number | null
  percentual_lido: number
  data_ultimo_acesso: string | null
  status: HistoricoStatus
}

export interface Lembrete {
  id: number
  missa_id: number | null
  titulo: string
  data_hora_alerta: string
  ativo: boolean
}

export interface UserPreferences {
  fontSize: 'small' | 'medium' | 'large' | 'extra-large'
  highContrast: boolean
  darkMode: boolean
}
