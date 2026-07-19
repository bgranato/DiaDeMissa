import { CantoCard } from './CantoCard'
import { DialogoCard } from './DialogoCard'
import { AntifonaCard } from './AntifonaCard'
import { LeituraCard } from './LeituraCard'

export default function BlocoRenderer({ bloco }: { bloco: any }) {
  const tipo = bloco.tipo || ''
  return <div>{renderConteudo(bloco, tipo)}</div>
}

// "Leituras da Semana" vem como um parágrafo único com todos os dias grudados
// ("20/2ª-FEIRA: ...; 21/3ª-FEIRA: ...; ..."). Quebramos em um dia por linha,
// com o dia em negrito, sem alterar o conteúdo. Retorna null se não casar.
const DIA_ABREV: Record<string, string> = {
  '2ª-FEIRA': 'Seg', '3ª-FEIRA': 'Ter', '4ª-FEIRA': 'Qua',
  '5ª-FEIRA': 'Qui', '6ª-FEIRA': 'Sex', 'SÁBADO': 'Sáb', 'DOMINGO': 'Dom',
}
function parseLeiturasSemana(texto: string) {
  const re = /(\d{1,2})\/(\d?ª-FEIRA|SÁBADO|DOMINGO):\s*/g
  const marcs: { idx: number; end: number; dia: string; rotulo: string }[] = []
  let m: RegExpExecArray | null
  while ((m = re.exec(texto)) !== null) {
    marcs.push({ idx: m.index, end: re.lastIndex, dia: m[1], rotulo: m[2] })
  }
  if (marcs.length < 2) return null
  return marcs.map((mk, i) => {
    const fim = i + 1 < marcs.length ? marcs[i + 1].idx : texto.length
    const corpo = texto.slice(mk.end, fim).trim().replace(/;\s*$/, '')
    const ci = corpo.indexOf(':')
    const santo = ci > -1 ? corpo.slice(0, ci).trim() : corpo
    const refs = ci > -1 ? corpo.slice(ci + 1).trim() : ''
    return { label: `${DIA_ABREV[mk.rotulo] || mk.rotulo}. ${mk.dia}`, santo, refs }
  })
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
    case 'salmo':
    case 'salmo_responsorial':
      // Salmo tem o mesmo formato do canto (refrão + estrofes).
      return <CantoCard canto={bloco} />
    case 'aclamacao':
    case 'aclamação_evangelho':
    case 'aclamacao_evangelho':
      // Aclamação: refrão + um versículo. Adapta o versículo como estrofe única
      // para reaproveitar o CantoCard.
      return (
        <CantoCard
          canto={{
            ...bloco,
            estrofes: bloco.versiculo ? [[bloco.versiculo]] : (bloco.estrofes || []),
          }}
        />
      )
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
    case 'recitacao': {
      const texto = bloco.texto || bloco.conteudo || ''
      // "Leituras da Semana": um dia por linha, dia em negrito.
      const dias = parseLeiturasSemana(texto)
      if (dias) {
        return (
          <div className="px-4 pb-4 pt-4 flex flex-col gap-2.5">
            {dias.map((d, i) => (
              <div key={i}>
                <p className="ds-body text-slate-800 dark:text-slate-200">
                  <span className="font-bold text-brand-text dark:text-slate-100">{d.label}</span>
                  {d.santo ? ` — ${d.santo}` : ''}
                </p>
                {d.refs && (
                  <p className="ds-body-sm text-slate-600 dark:text-slate-400 pl-4">{d.refs}</p>
                )}
              </div>
            ))}
          </div>
        )
      }
      // Texto recitado contínuo (Credo, Pai-Nosso, Oração Eucarística).
      return (
        <div className="px-4 pb-4 pt-4">
          <p className="ds-body text-slate-800 dark:text-slate-200 whitespace-pre-line">
            {texto}
          </p>
        </div>
      )
    }
    default:
      const textoFallback = bloco.conteudo || bloco.texto || ''
      if (textoFallback) {
        return (
          <div className="px-4 pb-4 pt-4">
            <p className="font-serif text-[18px] leading-[1.7] text-slate-800 dark:text-slate-200 whitespace-pre-wrap">
              {textoFallback}
            </p>
          </div>
        )
      }
      return (
        <div className="px-4 pb-4 pt-4">
          <p className="text-sm text-slate-500 italic">Bloco "{tipo}" em desenvolvimento.</p>
        </div>
      )
  }
}
