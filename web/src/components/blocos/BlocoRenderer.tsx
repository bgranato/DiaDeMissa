import { BlocoLiturgicoNovo } from '../../types/missa.nova'
import CantoCard from './CantoCard'
import LeituraCard from './LeituraCard'
import SalmoCard from './SalmoCard'
import AclamacaoCard from './AclamacaoCard'
import OracaoCard from './OracaoCard'
import DialogoCard from './DialogoCard'

const MAPA_TIPOS: Record<string, string> = {
  'canto_entrada': 'canto',
  'canto_de_entrada': 'canto',
  'canto_das_ofertas': 'canto',
  'canto_de_comunhão': 'canto',
  'canto_de_comunhao': 'canto',
  'canto_final': 'canto',
  'antifona_entrada': 'canto',
  'saudacao_inicial': 'dialogo',
  'ato_penitencial': 'dialogo',
  'gloria': 'canto',
  'oracao_dia': 'oracao',
  'primeira_leitura': 'leitura',
  'salmo_responsorial': 'salmo',
  'segunda_leitura': 'leitura',
  'aclamação_evangelho': 'aclamacao',
  'aclamação_ao_evangelho': 'aclamacao',
  'evangelho': 'leitura',
  'homilia': 'oracao',
  'profissao_fe': 'oracao',
  'preces_comunidade': 'dialogo',
  'ofertorio': 'canto',
  'santo': 'oracao',
  'oracao_eucaristica': 'oracao',
  'pai_nosso': 'oracao',
  'cordeiro_deus': 'oracao',
  'comunhao': 'canto',
  'oracao_pos_comunhao': 'oracao',
  'avisos': 'oracao',
  'bencao_final': 'dialogo',
  'desconhecido': 'oracao',
}

export default function BlocoRenderer({ bloco }: { bloco: BlocoLiturgicoNovo & { tipo: string } }) {
  const tipoNovo = MAPA_TIPOS[bloco.tipo] || bloco.tipo || 'oracao'

  switch (tipoNovo) {
    case 'canto':
      return <CantoCard bloco={bloco as any} />
    case 'leitura':
      return <LeituraCard bloco={bloco as any} />
    case 'salmo':
      return <SalmoCard bloco={bloco as any} />
    case 'aclamacao':
      return <AclamacaoCard bloco={bloco as any} />
    case 'oracao':
      return <OracaoCard bloco={bloco as any} />
    case 'dialogo':
      return <DialogoCard bloco={bloco as any} />
    default:
      return <CantoCard bloco={bloco as any} />
  }
}
