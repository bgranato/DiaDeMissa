import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { AppHeader } from '../components/UI'
import { getMissaAtual, getMissaEstruturadaPorData, salvarProgressoMissa, concluirMissa } from '../services/missa'
import { logError } from '../services/logger'
import BlocoRenderer from '../components/blocos/BlocoRenderer'
import { tituloDuplicaTexto, ordenarBlocos } from '../lib/blocoText'
import { List as ListIcon, X, Check, RotateCcw } from 'lucide-react'

interface Props {
  onBack: () => void
  onFinish: () => void
  missaId?: number
  missaDataAlvo?: string  // YYYY-MM-DD — usado quando acessa via Agenda
  registrarProgresso?: boolean
}

interface SectionInfo {
  titulo: string
  descricao?: string | null
  primeiraOcorrencia: boolean
}

interface BlocoLeitura {
  ordem?: number | null
  tipo?: string
  descricao?: string | null
  titulo?: string | null
  secao?: string | null
  [campo: string]: any
}

export const ReadingScreen = ({ onBack, onFinish, missaId, missaDataAlvo, registrarProgresso = true }: Props) => {
  const [todosBlocos, setTodosBlocos] = useState<BlocoLeitura[]>([])
  const [missaData, setMissaData] = useState<string | null>(null)
  const [missaTitulo, setMissaTitulo] = useState<string | null>(null)
  const [missaCategoria, setMissaCategoria] = useState<string | null>(null)
  const [missaObservacoes, setMissaObservacoes] = useState<string | null>(null)
  const [missaDescricao, setMissaDescricao] = useState<string | null>(null)
  const [descricaoExpandida, setDescricaoExpandida] = useState(false)
  const [missaCor, setMissaCor] = useState<string | null>(null)
  const [missaCreditos, setMissaCreditos] = useState<Record<string, string | null> | null>(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [showIndex, setShowIndex] = useState(false)
  const [showReiniciar, setShowReiniciar] = useState(false)
  const [loading, setLoading] = useState(true)

  const blocoRefs = useRef<(HTMLDivElement | null)[]>([])
  const restauradoRef = useRef(false)
  const indiceSalvoRef = useRef(0)

  useEffect(() => {
    // Prioridade: prop missaDataAlvo → localStorage @missa_data_alvo → missa de hoje.
    const dataDoStorage = localStorage.getItem('@missa_data_alvo')
    const dataParaBuscar = missaDataAlvo || dataDoStorage
    if (dataDoStorage) localStorage.removeItem('@missa_data_alvo')

    const fetcher = dataParaBuscar
      ? getMissaEstruturadaPorData(dataParaBuscar)
      : getMissaAtual()
    fetcher
      .then((missa: any) => {
        setTodosBlocos((missa.blocos || []) as BlocoLeitura[])
        const data = missa.data || null
        setMissaData(data)
        setMissaTitulo(missa.titulo_celebracao || null)
        setMissaCategoria(missa.categoria || null)
        setMissaObservacoes(missa.observacoes || null)
        setMissaCreditos(missa.creditos_cantos || null)
        const descRaw = missa.descricao || ''
        const cor = descRaw.match(/Cor\s+lit[uú]rgica:\s*(\w+)/i)
        setMissaCor(cor ? cor[1] : null)
        const ehSoCor = /^\s*Cor\s+lit[uú]rgica:/i.test(descRaw)
        setMissaDescricao(ehSoCor ? null : descRaw || null)
        // Guarda o bloco onde o usuário parou pra restaurar o scroll depois.
        if (data) {
          const salvo = Number(localStorage.getItem(`@missa_bloco_${data}`))
          if (Number.isFinite(salvo) && salvo > 0) indiceSalvoRef.current = salvo
        }
      })
      .catch(err => {
        console.error('Erro ao carregar missa:', err)
        setTodosBlocos([])
      })
      .finally(() => setLoading(false))
  }, [missaDataAlvo])

  // Marca "iniciada" quando o usuário passa do primeiro bloco (só abrir não conta).
  const marcarIniciada = () => {
    if (missaData && localStorage.getItem(`@missa_concluida_${missaData}`) !== 'true') {
      localStorage.setItem(`@missa_iniciada_${missaData}`, 'true')
    }
  }

  // Reconstrói a lista de blocos navegáveis + o mapa de seções (mesma lógica de antes).
  const { blocos, secaoPorIndice } = (() => {
    const list: BlocoLeitura[] = []
    const sec: Record<number, SectionInfo> = {}
    const descSec = new Map<string, string>()
    const secaoJaUsada = new Set<string>()

    // ORDEM ESTRITA da API: o renderer respeita o campo `ordem` do folheto e NÃO
    // reordena localmente (ex.: não puxa a Antífona da Comunhão para antes/depois
    // do "Momento de silêncio"). Cada bloco aparece exatamente na sua posição.
    const ordenados = ordenarBlocos<BlocoLeitura>(todosBlocos)

    for (const b of ordenados) {
      if (b.tipo === 'secao' && b.descricao) descSec.set(b.titulo, b.descricao)
    }

    for (const b of ordenados) {
      if (b.tipo === 'secao') continue
      const ehApendice = b.secao === 'apendice'
      const secaoTitulo = ehApendice ? null : (b.secao || null)
      const idxNovo = list.length
      list.push({ ...b, _ehApendice: ehApendice })
      if (secaoTitulo) {
        const primeira = !secaoJaUsada.has(secaoTitulo)
        sec[idxNovo] = {
          titulo: secaoTitulo,
          descricao: primeira ? (descSec.get(secaoTitulo) || null) : null,
          primeiraOcorrencia: primeira,
        }
        secaoJaUsada.add(secaoTitulo)
      }
    }
    return { blocos: list, secaoPorIndice: sec }
  })()

  // Scroll-spy: o "bloco atual" é o último cujo topo já passou logo abaixo do
  // cabeçalho + faixa (~130px). Mais preciso que IntersectionObserver p/ blocos altos.
  useEffect(() => {
    if (blocos.length === 0) return
    let raf = 0
    const atualizar = () => {
      raf = 0
      const limite = 130
      let atual = 0
      for (let i = 0; i < blocoRefs.current.length; i++) {
        const el = blocoRefs.current[i]
        if (!el) continue
        if (el.getBoundingClientRect().top <= limite) atual = i
        else break
      }
      setCurrentIndex(atual)
    }
    const onScroll = () => { if (!raf) raf = requestAnimationFrame(atualizar) }
    window.addEventListener('scroll', onScroll, { passive: true })
    atualizar()
    return () => { window.removeEventListener('scroll', onScroll); if (raf) cancelAnimationFrame(raf) }
  }, [blocos.length])

  // Restaura o scroll pro bloco onde o usuário parou (uma vez, após carregar).
  useEffect(() => {
    if (restauradoRef.current || loading || blocos.length === 0) return
    restauradoRef.current = true
    const salvo = indiceSalvoRef.current
    if (salvo > 0 && salvo < blocos.length) {
      setCurrentIndex(salvo)
      setTimeout(() => blocoRefs.current[salvo]?.scrollIntoView({ block: 'start' }), 120)
    }
  }, [loading, blocos.length])

  // Persiste progresso (debounced) sempre que o bloco atual muda.
  useEffect(() => {
    if (loading || blocos.length === 0) return
    if (missaData) localStorage.setItem(`@missa_bloco_${missaData}`, String(currentIndex))
    if (currentIndex > 0) marcarIniciada()
    if (!registrarProgresso || !missaId) return
    const t = setTimeout(() => {
      const bloco = blocos[currentIndex]
      const pct = Math.round(((currentIndex + 1) / blocos.length) * 100)
      salvarProgressoMissa(missaId, bloco?.id ?? bloco?.ordem ?? currentIndex, pct).catch(err =>
        logError('salvarProgressoMissa', err),
      )
    }, 800)
    return () => clearTimeout(t)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentIndex])

  const jumpTo = (index: number) => {
    setShowIndex(false)
    setCurrentIndex(index)
    blocoRefs.current[index]?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  const concluir = () => {
    if (registrarProgresso && missaId) concluirMissa(missaId).catch(err => logError('concluirMissa', err))
    if (missaData) {
      localStorage.setItem(`@missa_concluida_${missaData}`, 'true')
      localStorage.removeItem(`@missa_iniciada_${missaData}`)
      localStorage.removeItem(`@missa_bloco_${missaData}`)
    }
    onFinish()
  }

  // Navegação: só os blocos que o folheto NUMERA (nunca inventa número).
  const navEntries = blocos
    .map((b, i) => ({ i, n: b.numero_folheto as number | null | undefined }))
    .filter(e => e.n != null) as { i: number; n: number }[]
  // Entrada ativa = a do bloco atual, ou a última numerada antes dele (se o
  // atual for rubrica/antífona sem número).
  let currentNav = 0
  for (let k = 0; k < navEntries.length; k++) {
    if (navEntries[k].i <= currentIndex) currentNav = k
    else break
  }

  if (loading) return (
    <div className="min-h-screen bg-brand-bg dark:bg-slate-900 flex items-center justify-center">
      <div className="w-10 h-10 border-4 border-brand-gold border-t-transparent rounded-full animate-spin" />
    </div>
  )

  if (blocos.length === 0) return (
    <div className="min-h-screen bg-brand-bg dark:bg-slate-900 flex items-center justify-center p-8">
      <p className="text-brand-text/60 text-center">Nenhum bloco disponível para esta missa.</p>
    </div>
  )

  return (
    <div className="reading-wide min-h-[100svh] bg-brand-bg dark:bg-slate-900 pb-28">
      <AppHeader
        title=""
        onBack={onBack}
        showNotifications={false}
        rightElement={
          <div className="flex items-center gap-1">
            <button
              onClick={() => setShowReiniciar(true)}
              title="Reiniciar missa"
              className="p-2 text-brand-text dark:text-slate-100 active:scale-90 transition-transform"
            >
              <RotateCcw size={22} />
            </button>
            <button
              onClick={() => setShowIndex(true)}
              title="Roteiro da missa"
              className="p-2 text-brand-text dark:text-slate-100 active:scale-90 transition-transform"
            >
              <ListIcon size={24} />
            </button>
          </div>
        }
      />

      {/* Navegação — BARRA FIXA NO RODAPÉ, acompanha o scroll. Atual grande e
          centralizado; vizinhos (passados/futuros) menores e mais apagados.
          Só números REAIS do folheto (nunca inventa). */}
      {navEntries.length > 0 && (
        <div className="fixed bottom-0 inset-x-0 z-30 pointer-events-none">
          <div className="reading-wide mx-auto pointer-events-auto bg-brand-bg/90 dark:bg-slate-900/90 backdrop-blur-md border-t border-black/5 dark:border-white/10 shadow-[0_-4px_20px_rgba(0,0,0,0.08)]">
            <div className="flex items-center justify-center gap-1.5 px-3 pt-2 pb-[calc(0.5rem+env(safe-area-inset-bottom))]">
            {(() => {
              const start = Math.max(0, currentNav - 3)
              const end = Math.min(navEntries.length, currentNav + 4)
              const itens = []
              for (let k = start; k < end; k++) {
                const e = navEntries[k]
                const d = Math.abs(k - currentNav)
                const estilo =
                  d === 0 ? 'w-9 h-9 text-base bg-brand-gold text-white font-black shadow-soft'
                  : d === 1 ? 'w-7 h-7 text-sm bg-white dark:bg-slate-800 text-brand-blue dark:text-brand-gold font-bold'
                  : d === 2 ? 'w-6 h-6 text-xs bg-white/80 dark:bg-slate-800/80 text-brand-blue/50 dark:text-brand-gold/50 font-bold'
                  : 'w-5 h-5 text-[10px] bg-white/60 dark:bg-slate-800/60 text-brand-blue/30 dark:text-brand-gold/30 font-bold'
                itens.push(
                  <button
                    key={`nav-${e.i}`}
                    onClick={() => jumpTo(e.i)}
                    title={blocos[e.i]?.titulo}
                    className={`flex-shrink-0 rounded-full flex items-center justify-center transition-all active:scale-90 ${estilo}`}
                  >
                    {e.n}
                  </button>,
                )
              }
              return itens
            })()}
            </div>
          </div>
        </div>
      )}

      {/* Referência da missa */}
      {missaData && (
        <div className="ds-container pt-3 pb-1">
          <div className="border-l-4 border-brand-gold pl-3">
            <div className="flex items-center flex-wrap gap-2 mb-1">
              <span className="ds-pill ds-pill-gold">
                {new Date(missaData + 'T12:00:00').toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' }).toUpperCase()}
              </span>
              {missaCor && <span className="ds-section-label">Cor: {missaCor}</span>}
            </div>
            {missaTitulo && (
              <h1 className="ds-headline text-brand-blue dark:text-brand-white break-words">{missaTitulo}</h1>
            )}
            {(missaCategoria || missaObservacoes) && (
              <p className="ds-body-sm font-serif italic text-brand-slate dark:text-gray-300 break-words mt-1">
                {[missaCategoria, missaObservacoes].filter(Boolean).join(' · ')}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Apresentação do dia (texto introdutório) — sempre no topo da tripa. */}
      {missaDescricao && (
        <div className="ds-container pt-2">
          <div className="ds-card-subtle">
            <p
              className="ds-body-sm font-serif italic text-brand-slate dark:text-gray-300 whitespace-pre-line"
              style={!descricaoExpandida ? {
                overflow: 'hidden',
                display: '-webkit-box',
                WebkitBoxOrient: 'vertical',
                WebkitLineClamp: 3,
                textOverflow: 'ellipsis',
              } : {}}
            >
              {missaDescricao}
            </p>
            {missaDescricao.length > 120 && (
              <button
                onClick={() => setDescricaoExpandida(!descricaoExpandida)}
                className="ds-caption font-bold text-brand-gold mt-1 hover:opacity-80 active:scale-95 transition-transform"
              >
                {descricaoExpandida ? '↑ Ver menos' : '↓ Ver mais'}
              </button>
            )}
          </div>
        </div>
      )}

      {/* Créditos dos cantos (do folheto) — pequenos, sob a apresentação. */}
      {missaCreditos && (missaCreditos.entrada || missaCreditos.ofertas || missaCreditos.comunhao || missaCreditos.final) && (
        <div className="ds-container pt-2">
          <div className="ds-card-subtle">
            <p className="ds-section-label text-brand-gold mb-1">Cantos</p>
            <div className="ds-caption text-brand-slate dark:text-gray-400 leading-relaxed space-y-0.5">
              {missaCreditos.entrada && <p><span className="font-bold">Entrada{missaCreditos.comunhao === missaCreditos.entrada ? ' e Comunhão' : ''}:</span> {missaCreditos.entrada}</p>}
              {missaCreditos.comunhao && missaCreditos.comunhao !== missaCreditos.entrada && <p><span className="font-bold">Comunhão:</span> {missaCreditos.comunhao}</p>}
              {missaCreditos.ofertas && <p><span className="font-bold">Ofertas:</span> {missaCreditos.ofertas}</p>}
              {missaCreditos.final && <p><span className="font-bold">Final:</span> {missaCreditos.final}</p>}
            </div>
          </div>
        </div>
      )}

      {/* Tripa única — todos os blocos num scroll contínuo. */}
      <div className="ds-container pt-4" id="reading-content">
        {blocos.map((bloco, i) => {
          const secao = secaoPorIndice[i]
          return (
            <div
              key={bloco.ordem ?? i}
              ref={el => { blocoRefs.current[i] = el }}
              data-index={i}
              className="scroll-mt-28 mb-8"
            >
              {/* Cabeçalho de seção (só na primeira ocorrência) */}
              {secao && secao.primeiraOcorrencia && (
                <div className="mb-3 pb-3 border-b border-brand-gold/15">
                  <p className="ds-section-label mb-2">{secao.titulo}</p>
                  {secao.descricao && (
                    <p className="ds-body-sm font-serif italic text-brand-slate dark:text-gray-300">
                      {secao.descricao}
                    </p>
                  )}
                </div>
              )}

              {/* Apêndice (Leituras da Semana etc.) */}
              {bloco._ehApendice && (
                <div className="ds-card-subtle mb-3 flex flex-col gap-0.5">
                  <span className="ds-section-label text-brand-gold">Conteúdo Complementar</span>
                  <span className="ds-body-sm font-serif italic text-brand-slate dark:text-gray-300 [overflow-wrap:normal] [word-break:normal] hyphens-none">
                    para aprofundar com base na liturgia
                  </span>
                </div>
              )}

              <div className="flex items-start justify-between gap-3 mb-3">
                <div className={`flex-1 min-w-0 ${bloco.numero_folheto != null ? 'border-l-4 border-brand-gold pl-3' : 'pl-1'}`}>
                  {/* A4 — se o corpo apenas repete o título, não exibe o título aqui
                     (o BlocoRenderer mostra o texto uma vez, em estilo de rubrica). */}
                  {tituloDuplicaTexto(bloco.titulo, bloco.texto) ? null : bloco.numero_folheto != null ? (
                    <h2 className="ds-headline text-brand-text dark:text-slate-100 break-words">
                      {`${bloco.numero_folheto}. ${bloco.titulo}`}
                    </h2>
                  ) : (
                    /* Sem número no folheto (rubrica/antífona) → título leve, sem barra. */
                    <h2 className="ds-title font-serif italic text-brand-slate dark:text-gray-300 break-words">
                      {bloco.titulo}
                    </h2>
                  )}
                  {bloco.introducao && (
                    <p className="ds-body-sm font-serif italic text-brand-slate dark:text-gray-300 mt-0.5">{bloco.introducao}</p>
                  )}
                  {bloco.subtitulo && (
                    <p className="ds-body-sm font-serif italic text-brand-slate dark:text-gray-300 mt-0.5">{bloco.subtitulo}</p>
                  )}
                  {bloco.referencia && (
                    <span className="ds-caption italic font-serif text-brand-slate dark:text-gray-400 block mt-0.5">{bloco.referencia}</span>
                  )}
                </div>
                {bloco.postura && (
                  <span className="ds-pill ds-pill-ghost flex-shrink-0 mt-1">
                    {bloco.postura === 'de_pe' ? 'De pé' : bloco.postura === 'sentado' ? 'Sentado' : bloco.postura === 'ajoelhado' ? 'Ajoelhado' : bloco.postura}
                  </span>
                )}
              </div>

              <div className="reading-block">
                <BlocoRenderer bloco={bloco} />
                {bloco.antifonas_anexadas?.map((a: any, k: number) => (
                  <div key={`ant-${k}`} className="px-4 py-3 mt-2 border-t border-brand-gold/20">
                    <p className="ds-section-label text-brand-gold mb-1">{a.titulo}</p>
                    {a.referencia && (
                      <p className="ds-caption italic font-serif text-brand-slate dark:text-gray-400 mb-1">({a.referencia})</p>
                    )}
                    <p className="ds-body italic text-slate-700 dark:text-slate-300 whitespace-pre-line">{a.texto}</p>
                  </div>
                ))}
              </div>
            </div>
          )
        })}

        {/* Concluir missa — no fim da tripa (substitui o antigo botão Próximo/Concluir). */}
        <div className="mt-4 mb-2">
          <button
            onClick={concluir}
            className="w-full flex items-center justify-center gap-2 rounded-2xl bg-brand-gold text-white font-black py-4 shadow-strong active:scale-95 transition-transform"
          >
            <Check size={20} /> Concluir missa
          </button>
        </div>
      </div>

      {/* Roteiro (índice) */}
      <AnimatePresence>
        {showIndex && (
          <>
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
              onClick={() => setShowIndex(false)}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[100]"
            />
            <motion.div
              initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed bottom-0 left-0 right-0 bg-white dark:bg-slate-800 rounded-t-[40px] z-[101] max-h-[85vh] overflow-hidden flex flex-col shadow-2xl"
            >
              <div className="p-6 pb-2 border-b border-gray-100 dark:border-slate-700 flex items-center justify-between">
                <h3 className="text-xl font-bold dark:text-white">Roteiro da Missa</h3>
                <button onClick={() => setShowIndex(false)} className="p-2 bg-gray-100 dark:bg-slate-700 rounded-full">
                  <X size={20} />
                </button>
              </div>
              <div className="overflow-y-auto p-4 flex flex-col gap-2 pb-10">
                {(() => {
                  const elementos: any[] = []
                  let ultimaSecao: string | null = null
                  blocos.forEach((block, idx) => {
                    const secao = secaoPorIndice[idx]
                    if (secao && secao.titulo !== ultimaSecao) {
                      ultimaSecao = secao.titulo
                      elementos.push(
                        <div key={`secao-${idx}`} className="pt-3 pb-1 px-2 text-[11px] uppercase tracking-[0.3em] text-brand-gold font-black border-b border-brand-gold/20">
                          {secao.titulo}
                        </div>,
                      )
                    }
                    elementos.push(
                      <button key={`bloco-${block.ordem ?? idx}`} onClick={() => jumpTo(idx)}
                        className={`flex items-center gap-4 p-4 rounded-2xl text-left transition-colors ${
                          currentIndex === idx ? 'bg-brand-blue text-white shadow-md' : 'bg-gray-50 dark:bg-slate-700/50 hover:bg-gray-100 dark:hover:bg-slate-700'
                        }`}
                      >
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm ${
                          currentIndex === idx ? 'bg-white text-brand-blue' : 'bg-gray-200 dark:bg-slate-600 text-gray-500'
                        }`}>
                          {block.numero_folheto ?? (idx + 1)}
                        </div>
                        <div className="flex-1">
                          <p className="font-bold leading-tight">{block.titulo}</p>
                          <p className="text-xs uppercase tracking-wider opacity-70">{(block.tipo || '').replace(/_/g, ' ')}</p>
                        </div>
                      </button>,
                    )
                  })
                  return elementos
                })()}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Reiniciar */}
      <AnimatePresence>
        {showReiniciar && (
          <motion.div
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center px-5"
            onClick={() => setShowReiniciar(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} exit={{ scale: 0.9, opacity: 0 }}
              className="bg-white dark:bg-slate-900 rounded-3xl w-full max-w-sm p-6 shadow-strong"
              onClick={e => e.stopPropagation()}
            >
              <div className="w-14 h-14 rounded-full bg-brand-gold/15 flex items-center justify-center mx-auto mb-4">
                <RotateCcw size={28} className="text-brand-gold" />
              </div>
              <h3 className="text-xl font-serif font-black text-brand-blue dark:text-brand-white text-center mb-2">Reiniciar missa?</h3>
              <p className="text-sm text-brand-gray-dark/70 dark:text-brand-white/70 text-center mb-6">
                Você voltará pro início e seu progresso será apagado. Local da missa e marcação de concluída também serão resetados.
              </p>
              <div className="flex gap-2">
                <button
                  onClick={() => setShowReiniciar(false)}
                  className="flex-1 py-3 rounded-2xl bg-gray-100 dark:bg-slate-800 text-brand-gray-dark dark:text-brand-white font-black text-sm active:scale-95 transition-transform"
                >
                  Cancelar
                </button>
                <button
                  onClick={() => {
                    if (missaData) {
                      localStorage.removeItem(`@missa_bloco_${missaData}`)
                      localStorage.removeItem(`@missa_iniciada_${missaData}`)
                      localStorage.removeItem(`@missa_concluida_${missaData}`)
                    }
                    setCurrentIndex(0)
                    setShowReiniciar(false)
                    if (registrarProgresso && missaId) {
                      import('../services/api').then(({ default: api }) => {
                        api.post(`/usuarios/me/historico/${missaId}/desconcluir`).catch(() => { })
                      })
                    }
                    window.scrollTo({ top: 0, behavior: 'smooth' })
                  }}
                  className="flex-1 py-3 rounded-2xl bg-brand-gold text-white font-black text-sm active:scale-95 transition-transform shadow-soft"
                >
                  Reiniciar
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
