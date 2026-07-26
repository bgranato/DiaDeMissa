import { CantoCard } from './CantoCard'
import { DialogoCard } from './DialogoCard'
import { AntifonaCard } from './AntifonaCard'
import { LeituraCard } from './LeituraCard'
import { parseLeiturasSemana, tituloDuplicaTexto, ehVivencia } from '../../lib/blocoText'

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
      // A4 — Título ≈ texto (ex.: "Momento de silêncio para oração pessoal"):
      // o corpo só repete o título → exibe uma vez, em estilo de rubrica.
      if (tituloDuplicaTexto(bloco.titulo, texto)) {
        return (
          <div className="px-4 pb-4 pt-2">
            <p className="ds-body-sm italic text-center text-slate-500 dark:text-slate-400">{texto}</p>
          </div>
        )
      }
      // A5 — Vivência: exibe o chip "L" (Leitor), decidido pelo TÍTULO.
      if (ehVivencia(bloco.titulo)) {
        return (
          <div className="px-4 pb-4 pt-4">
            <div className="flex gap-2 items-start">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-slate-100 text-slate-600 text-[10px] font-bold flex items-center justify-center mt-0.5">L</span>
              <p className="ds-body text-slate-800 dark:text-slate-200 flex-1 whitespace-pre-line">{texto}</p>
            </div>
          </div>
        )
      }
      // Texto recitado contínuo (Credo, Pai-Nosso, Oração Eucarística, Coleta…).
      // Se o bloco tiver `resposta` (ex.: "Amém." da assembleia), renderiza com o
      // chip T — esses blocos podem vir como tipo "oracao" (não só "dialogo").
      return (
        <div className="px-4 pb-4 pt-4 ds-stack-sm">
          <p className="ds-body text-slate-800 dark:text-slate-200 whitespace-pre-line">
            {texto}
          </p>
          {bloco.resposta && (
            <div className="flex gap-2 items-start">
              <span className="flex-shrink-0 w-5 h-5 rounded-full bg-amber-100 text-amber-700 text-[10px] font-bold flex items-center justify-center mt-0.5">T</span>
              <p className="ds-body font-bold text-slate-800 dark:text-slate-200 flex-1">{bloco.resposta}</p>
            </div>
          )}
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
