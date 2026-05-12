import { CantoCard } from './CantoCard'
import { DialogoCard } from './DialogoCard'
import { AntifonaCard } from './AntifonaCard'
import { LeituraCard } from './LeituraCard'

export default function BlocoRenderer({ bloco }: { bloco: any }) {
  const tipo = bloco.tipo || ''
  const titulo = bloco.titulo || ''

  return (
    <div>
      {titulo && (
        <div className="flex items-center gap-3 px-4 pt-4 pb-1">
          <h2 className="font-serif font-black text-xl text-brand-blue dark:text-brand-white">{titulo}</h2>
        </div>
      )}
      {renderConteudo(bloco, tipo)}
    </div>
  )
}

function renderConteudo(bloco: any, tipo: string) {
  switch (tipo) {
    case 'canto':
    case 'canto_entrada':
    case 'canto_de_entrada':
    case 'canto_das_ofertas':
    case 'canto_de_comunhão':
    case 'gloria':
    case 'hino_de_louvor':
      return <CantoCard canto={bloco} />
    case 'dialogo':
    case 'saudacao_inicial':
    case 'ato_penitencial':
    case 'preces_comunidade':
    case 'bencao_final':
      return <DialogoCard dialogo={bloco} />
    case 'antifona':
    case 'antifona_entrada':
      return <AntifonaCard antifona={bloco} />
    case 'leitura':
    case 'primeira_leitura':
    case 'segunda_leitura':
    case 'evangelho':
      return <LeituraCard leitura={bloco} />
    default:
      if (bloco.conteudo) {
        return (
          <div className="px-4 pb-4">
            <p className="text-[17px] leading-[1.6] text-slate-700 whitespace-pre-wrap">{bloco.conteudo}</p>
          </div>
        )
      }
      return (
        <div className="px-4 pb-4">
          <p className="text-sm text-slate-500 italic">Bloco "{tipo}" em desenvolvimento.</p>
        </div>
      )
  }
}
