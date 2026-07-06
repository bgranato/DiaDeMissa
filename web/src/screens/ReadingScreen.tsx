import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { AppHeader } from '../components/UI'
import { getMissaAtual, getMissaEstruturadaPorData, salvarProgressoMissa, concluirMissa } from '../services/missa'
import { logError } from '../services/logger'
import BlocoRenderer from '../components/blocos/BlocoRenderer'
import { List as ListIcon, X, Check, RotateCcw } from 'lucide-react'

interface Props {
  onBack: () => void
  onFinish: () => void
  missaId?: number
  missaDataAlvo?: string  // YYYY-MM-DD — usado quando acessa via Agenda
}

interface SectionInfo {
  titulo: string
  descricao?: string | null
  primeiraOcorrencia: boolean
}

export const ReadingScreen = ({ onBack, onFinish, missaId, missaDataAlvo }: Props) => {
  const [todosBlocos, setTodosBlocos] = useState<any[]>([])
  const [missaData, setMissaData] = useState<string | null>(null)
  const [missaTitulo, setMissaTitulo] = useState<string | null>(null)
  const [missaCategoria, setMissaCategoria] = useState<string | null>(null)
  const [missaObservacoes, setMissaObservacoes] = useState<string | null>(null)
  const [missaDescricao, setMissaDescricao] = useState<string | null>(null)
  const [descricaoExpandida, setDescricaoExpandida] = useState(false)
  const [missaCor, setMissaCor] = useState<string | null>(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [showIndex, setShowIndex] = useState(false)
  const [showReiniciar, setShowReiniciar] = useState(false)
  const [loading, setLoading] = useState(true)

  const blocoRefs = useRef<(HTMLDivElement | null)[]>([])
  const markerRef = useRef<HTMLDivElement>(null)
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
        setTodosBlocos(missa.blocos || [])
        const data = missa.data || null
        setMissaData(data)
        setMissaTitulo(missa.titulo_celebracao || null)
        setMissaCategoria(missa.categoria || null)
        setMissaObservacoes(missa.observacoes || null)
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
    const list: any[] = []
    const sec: Record<number, SectionInfo> = {}
    const descSec = new Map<string, string>()
    const secaoJaUsada = new Set<string>()

    for (const b of todosBlocos) {
      if (b.tipo === 'secao' && b.descricao) descSec.set(b.titulo, b.descricao)
    }

    const ehAntifonaAnexavel = (b: any) => {
      if (b.tipo !== 'antifona') return false
      const t = (b.titulo || '').toLowerCase()
      return t.includes('entrada') || t.includes('comunhão') || t.includes('comunhao')
    }

    for (const b of todosBlocos) {
      if (b.tipo === 'secao') continue
      if (ehAntifonaAnexavel(b)) {
        const ultimo = list[list.length - 1]
        if (ultimo) {
          ultimo.antifonas_anexadas = ultimo.antifonas_anexadas || []
          ultimo.antifonas_anexadas.push({
            titulo: b.titulo,
            texto: b.texto || b.conteudo || '',
            referencia: b.referencia || null,
          })
          continue
        }
      }
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

  // Scroll-spy: detecta qual bloco está na faixa logo abaixo do topo → vira o "atual".
  useEffect(() => {
    if (blocos.length === 0) return
    const obs = new IntersectionObserver(
      (entries) => {
        const visiveis = entries
          .filter(e => e.isIntersecting)
          .map(e => Number((e.target as HTMLElement).dataset.index))
          .filter(n => Number.isFinite(n))
        if (visiveis.length) setCurrentIndex(Math.min(...visiveis))
      },
      { rootMargin: '-104px 0px -78% 0px', threshold: 0 },
    )
    blocoRefs.current.forEach(el => el && obs.observe(el))
    return () => obs.disconnect()
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

  // Centraliza a faixa de números no bloco atual.
  useEffect(() => {
    const strip = markerRef.current
    if (!strip) return
    const pill = strip.querySelector(`[data-marker="${currentIndex}"]`) as HTMLElement | null
    if (pill) {
      strip.scrollTo({ left: pill.offsetLeft - strip.clientWidth / 2 + pill.clientWidth / 2, behavior: 'smooth' })
    }
  }, [currentIndex])

  // Persiste progresso (debounced) sempre que o bloco atual muda.
  useEffect(() => {
    if (loading || blocos.length === 0) return
    if (missaData) localStorage.setItem(`@missa_bloco_${missaData}`, String(currentIndex))
    if (currentIndex > 0) marcarIniciada()
    if (!missaId) return
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
    if (missaId) concluirMissa(missaId).catch(err => logError('concluirMissa', err))
    if (missaData) {
      localStorage.setItem(`@missa_concluida_${missaData}`, 'true')
      localStorage.removeItem(`@missa_iniciada_${missaData}`)
      localStorage.removeItem(`@missa_bloco_${missaData}`)
    }
    onFinish()
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
    <div className="reading-wide min-h-[100svh] bg-brand-bg dark:bg-slate-900 pb-24">
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

      {/* Marcador de posição — faixa de números sticky, rola e centraliza o atual. */}
      <div className="sticky top-14 z-20 bg-brand-bg/95 dark:bg-slate-900/95 backdrop-blur-md border-b border-black/[0.06] dark:border-white/[0.06]">
        <div ref={markerRef} className="flex gap-1.5 overflow-x-auto px-3 py-2" style={{ scrollbarWidth: 'none' }}>
          {blocos.map((b, i) => (
            <button
              key={`m-${b.ordem ?? i}`}
              data-marker={i}
              onClick={() => jumpTo(i)}
              title={b.titulo}
              className={`flex-shrink-0 min-w-[2rem] h-8 px-2 rounded-full text-xs font-black transition-all ${
                i === currentIndex
                  ? 'bg-brand-gold text-white scale-110 shadow-soft'
                  : 'bg-white dark:bg-slate-800 text-brand-blue/60 dark:text-brand-gold/50 border border-black/5'
              }`}
            >
              {b.numero_folheto ?? (i + 1)}
            </button>
          ))}
        </div>
      </div>

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
              {secao && (
                <div className="mb-3 pb-3 border-b border-brand-gold/15">
                  <p className="ds-section-label mb-2">{secao.titulo}</p>
                  {secao.primeiraOcorrencia && secao.descricao && (
                    <p className="ds-body-sm font-serif italic text-brand-slate dark:text-gray-300">
                      {secao.descricao}
                    </p>
                  )}
                </div>
              )}

              {/* Apêndice (Leituras da Semana etc.) */}
              {bloco._ehApendice && (
                <div className="ds-card-subtle mb-3 flex items-start gap-2">
                  <span className="ds-section-label text-brand-gold whitespace-nowrap mt-0.5">Conteúdo Complementar</span>
                  <span className="ds-body-sm font-serif italic text-brand-slate dark:text-gray-300">
                    · para aprofundar com base na liturgia
                  </span>
                </div>
              )}

              <div className="flex items-start justify-between gap-3 mb-3">
                <div className="border-l-4 border-brand-gold pl-3 flex-1 min-w-0">
                  <h2 className="ds-headline text-brand-text dark:text-slate-100 break-words">
                    {bloco._ehApendice ? bloco.titulo : `${bloco.numero_folheto ?? (i + 1)}. ${bloco.titulo}`}
                  </h2>
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
                    if (missaId) {
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
