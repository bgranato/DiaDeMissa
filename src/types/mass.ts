export type LiturgicalBlockType = 
  | 'canto_entrada' 
  | 'ato_penitencial'
  | 'gloria'
  | 'oracao_dia'
  | 'primeira_leitura' 
  | 'salmo_responsorial' 
  | 'segunda_leitura' 
  | 'aclamacao_evangelho' 
  | 'evangelho' 
  | 'homilia'
  | 'credo'
  | 'preces_comunidade' 
  | 'ofertario' 
  | 'santo'
  | 'oracao_eucaristica'
  | 'pai_nosso'
  | 'comunhao' 
  | 'oracao_pos_comunhao' 
  | 'bencao_final';

export interface LiturgicalBlock {
  ordem: number;
  tipo: LiturgicalBlockType;
  titulo: string;
  referencia?: string | null;
  conteudo: string;
}

export interface Mass {
  id: string;
  data: string;
  celebracao: string;
  tempo_liturgico: string;
  resumo: string;
  blocos: LiturgicalBlock[];
}

export interface UserPreferences {
  fontSize: 'small' | 'medium' | 'large' | 'extra-large';
  highContrast: boolean;
  darkMode: boolean;
}

export interface UserReminder {
  id: string;
  horario: string;
  celebracao: string;
  ativo: boolean;
  visto: boolean;
}

export interface HistoryItem {
  id: string;
  massId: string;
  celebracao: string;
  data: string;
  progresso: number; // 0 to 100
}
