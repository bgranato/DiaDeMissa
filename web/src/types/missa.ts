export interface PalavraDoDia {
  texto: string
  referencia: string
}

export interface Missa {
  id: number
  data: string
  celebracao: string | null
  subtitulo: string | null
  descricao: string | null
  tempo_liturgico: string | null
  status_processamento: string
  total_blocos: number
  palavra_do_dia?: PalavraDoDia | null
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
