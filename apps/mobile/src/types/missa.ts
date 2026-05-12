export interface Missa {
  id: number
  data: string
  celebracao: string | null
  tempo_liturgico: string | null
  status_processamento: string
  total_blocos: number
}

export interface BlocoLiturgico {
  id: number
  ordem: number
  tipo: string
  titulo: string | null
  referencia: string | null
  conteudo: string | null
  visivel: boolean
}

export interface MissaCompleta {
  id: number
  data: string
  celebracao: string | null
  tempo_liturgico: string | null
  fonte_pdf_url: string
  pdf_hash: string | null
  status_processamento: string
  data_criacao: string
  blocos: BlocoLiturgico[]
}

export type TipoBloco =
  | 'canto_entrada'
  | 'antifona_entrada'
  | 'saudacao_inicial'
  | 'ato_penitencial'
  | 'gloria'
  | 'oracao_dia'
  | 'primeira_leitura'
  | 'salmo_responsorial'
  | 'segunda_leitura'
  | 'sequencia'
  | 'aclamação_evangelho'
  | 'evangelho'
  | 'homilia'
  | 'profissao_fe'
  | 'preces_comunidade'
  | 'ofertorio'
  | 'santo'
  | 'oracao_eucaristica'
  | 'pai_nosso'
  | 'cordeiro_deus'
  | 'comunhao'
  | 'oracao_pos_comunhao'
  | 'avisos'
  | 'bencao_final'
  | 'canto_final'
  | 'desconhecido'
