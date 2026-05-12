export interface Creditos {
  entrada?: string | null
  ofertas?: string | null
  comunhao?: string | null
  final?: string | null
  observacoes?: string | null
}

export type Postura = 'de_pe' | 'sentado' | 'ajoelhado' | null

export interface Canto {
  tipo: 'canto'
  titulo: string
  postura: Postura
  refrao: string[]
  estrofes: string[][]
  creditos?: Creditos | null
}

export interface Leitura {
  tipo: 'primeira_leitura' | 'segunda_leitura' | 'evangelho'
  titulo: string
  referencia: string
  introducao: string
  texto: string
  conclusao?: string | null
  postura: Postura
}

export interface Salmo {
  tipo: 'salmo'
  titulo: string
  referencia: string
  refrao: string[]
  estrofes: string[][]
  postura: Postura
}

export interface Aclamacao {
  tipo: 'aclamacao'
  titulo: string
  refrao: string[]
  versiculo: string
  postura: Postura
}

export interface Oracao {
  tipo: 'oracao'
  titulo: string
  texto: string
  resposta?: string | null
  postura: Postura
}

export interface TurnoDialogo {
  falante: string
  texto: string
}

export interface Dialogo {
  tipo: 'dialogo'
  titulo: string
  turnos: TurnoDialogo[]
  postura: Postura
}

export type BlocoLiturgicoNovo = Canto | Leitura | Salmo | Aclamacao | Oracao | Dialogo

export interface MissaNova {
  data: string
  titulo_celebracao: string
  tempo_liturgico?: string | null
  cor_liturgica?: string | null
  observacoes?: string | null
  blocos: BlocoLiturgicoNovo[]
}
