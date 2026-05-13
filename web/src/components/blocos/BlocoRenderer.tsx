import { CantoCard } from './CantoCard'
import { DialogoCard } from './DialogoCard'
import { AntifonaCard } from './AntifonaCard'
import { LeituraCard } from './LeituraCard'

export default function BlocoRenderer({ bloco }: { bloco: any }) {
  const tipo = bloco.tipo || ''
  return <div>{renderConteudo(bloco, tipo)}</div>
}

function renderConteudo(bloco: any, tipo: string) {
  switch (tipo) {
    case 'secao':
      return (
        <div className="px-4 py-6 text-center">
          {bloco.descricao && (
            <p className="text-base font-serif italic text-brand-slate dark:text-gray-300 leading-relaxed">
              {bloco.descricao}
            </p>
          )}
          {!bloco.descricao && (
            <p className="text-sm uppercase tracking-[0.3em] text-brand-gold/70 font-bold">
              Iniciando esta parte da celebração
            </p>
          )}
        </div>
      )
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
    case 'oracao':
      return (
        <div className="px-4 pb-4">
          <p className="text-[18px] leading-[1.8] text-slate-700 whitespace-pre-wrap">{bloco.texto || bloco.conteudo || ''}</p>
        </div>
      )
    default:
      const textoFallback = bloco.conteudo || bloco.texto || ''
      if (textoFallback) {
        return (
          <div className="px-4 pb-4">
            <p className="text-[17px] leading-[1.6] text-slate-700 whitespace-pre-wrap">{textoFallback}</p>
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
