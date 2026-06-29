import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { AppHeader } from '../components/UI'
import { getMissaAtual, getMissaEstruturadaPorData, salvarProgressoMissa, concluirMissa } from '../services/missa'
import { logError } from '../services/logger'
import BlocoRenderer from '../components/blocos/BlocoRenderer'
import { ChevronLeft, ChevronRight, List as ListIcon, X, Check, RotateCcw } from 'lucide-react'

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
  const contentRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Prioridade pra carregar a missa:
    // 1. Prop `missaDataAlvo` (se foi passada explicitamente pelo App)
    // 2. localStorage `@missa_data_alvo` (setado pela Agenda antes de navegar)
    // 3. Missa de hoje (default — vindo da Home)
    const dataDoStorage = localStorage.getItem('@missa_data_alvo')
    const dataParaBuscar = missaDataAlvo || dataDoStorage
    // Consome a chave do localStorage uma vez (pra não persistir na próxima abertura)
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
        // Descrição é o texto introdutório ("Neste Domingo, ..."). Não confundir
        // com o campo que carrega "Cor litúrgica:" (usado pela liturgia diária CNBB).
        const descRaw = missa.descricao || ''
        const cor = descRaw.match(/Cor\s+lit[uú]rgica:\s*(\w+)/i)
        setMissaCor(cor ? cor[1] : null)
        const ehSoCor = /^\s*Cor\s+lit[uú]rgica:/i.test(descRaw)
        setMissaDescricao(ehSoCor ? null : descRaw || null)
        // Restaura o bloco onde o usuário parou (se houver registro local)
        if (data) {
          const salvo = Number(localStorage.getItem(`@missa_bloco_${data}`))
          if (Number.isFinite(salvo) && salvo > 0) {
            setCurrentIndex(salvo)
          }
        }
      })
      .catch(err => {
        console.error('Erro ao carregar missa:', err)
        setTodosBlocos([])
      })
      .finally(() => setLoading(false))
  }, [missaDataAlvo])

  // Marca a missa como "iniciada" só na primeira vez que o usuário avança
  // (currentIndex sai de 0). Apenas abrir a tela não conta como iniciar.
  const marcarIniciada = () => {
    if (missaData && localStorage.getItem(`@missa_concluida_${missaData}`) !== 'true') {
      localStorage.setItem(`@missa_iniciada_${missaData}`, 'true')
    }
  }

  // Reconstrói a lista navegável a partir da estrutura que JÁ VEM do backend:
  // - Cada bloco carrega `secao` (Ritos Iniciais, Liturgia da Palavra, ...) e
  //   `numero_folheto` (numeração original do folheto: 1, 2, 6, 7…).
  // - Antífonas da Entrada/Comunhão já vêm anexadas ao Canto correspondente
  //   como `antifona_anexada` — não são blocos próprios.
  // - Apêndices (Leituras da Semana, Antífona Mariana, Oração Comunicações)
  //   ficam com `secao = 'apendice'`.
  // O front aqui apenas separa: lista de blocos navegáveis (sem `secao`) e
  // mapeia, pra cada bloco, sua seção pra exibir o cabeçalho.
  const { blocos, secaoPorIndice, descricaoPorSecao } = (() => {
    const list: any[] = []
    const sec: Record<number, SectionInfo> = {}
    const descSec = new Map<string, string>()
    let secaoJaUsada = new Set<string>()

    // Primeiro, indexa descrições das seções (vêm em blocos tipo='secao')
    for (const b of todosBlocos) {
      if (b.tipo === 'secao' && b.descricao) {
        descSec.set(b.titulo, b.descricao)
      }
    }

    // Antífonas da Entrada/Comunhão são anexadas como aditivo do bloco anterior
    // (rendering only — não geram slide próprio, não incrementam numeração).
    // Antífona Mariana e outras antífonas continuam como blocos próprios.
    const ehAntifonaAnexavel = (b: any) => {
      if (b.tipo !== 'antifona') return false
      const t = (b.titulo || '').toLowerCase()
      return t.includes('entrada') || t.includes('comunhão') || t.includes('comunhao')
    }

    for (const b of todosBlocos) {
      if (b.tipo === 'secao') continue
      // Anexa antífona ao último bloco navegável pushado (não cria slide próprio)
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
      // Apêndices (Leituras da Semana, Antífona Mariana, Oração Comunicações)
      // NÃO recebem cabeçalho de seção — são conteúdos agregados/complementares,
      // não fazem parte da estrutura litúrgica.
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
    return { blocos: list, secaoPorIndice: sec, descricaoPorSecao: descSec }
  })()

  const currentBlock = blocos[currentIndex]
  const secaoAtual = secaoPorIndice[currentIndex]
  const isLastBlock = currentIndex === blocos.length - 1
  const progress = blocos.length > 0 ? Math.round(((currentIndex + 1) / blocos.length) * 100) : 0

  const scrollToTop = () => {
    // O scroll real acontece na window (contentRef é div sem overflow).
    window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior })
    document.documentElement.scrollTop = 0
    document.body.scrollTop = 0
  }

  const persistirProgresso = (index: number) => {
    if (blocos.length === 0) return
    // Salva localmente pra "Continuar de onde parei" voltar pro mesmo bloco
    if (missaData) {
      localStorage.setItem(`@missa_bloco_${missaData}`, String(index))
    }
    if (!missaId) return
    const bloco = blocos[index]
    const pct = Math.round(((index + 1) / blocos.length) * 100)
    salvarProgressoMissa(missaId, bloco?.id ?? bloco?.ordem ?? index, pct).catch(err =>
      logError('salvarProgressoMissa', err),
    )
  }

  const nextBlock = () => {
    if (!isLastBlock) {
      const next = currentIndex + 1
      setCurrentIndex(next)
      scrollToTop()
      persistirProgresso(next)
      marcarIniciada()
    } else {
      if (missaId) {
        concluirMissa(missaId).catch(err => logError('concluirMissa', err))
      }
      if (missaData) {
        localStorage.setItem(`@missa_concluida_${missaData}`, 'true')
        localStorage.removeItem(`@missa_iniciada_${missaData}`)
        localStorage.removeItem(`@missa_bloco_${missaData}`)
      }
      onFinish()
    }
  }
  const prevBlock = () => {
    if (currentIndex > 0) {
      const prev = currentIndex - 1
      setCurrentIndex(prev)
      scrollToTop()
      persistirProgresso(prev)
    }
  }
  const jumpTo = (index: number) => {
    setCurrentIndex(index)
    setShowIndex(false)
    scrollToTop()
    persistirProgresso(index)
  }

  if (loading) return (
    <div className="min-h-screen bg-brand-bg dark:bg-slate-900 flex items-center justify-center">
      <div className="w-10 h-10 border-4 border-brand-gold border-t-transparent rounded-full animate-spin" />
    </div>
  )

  if (!currentBlock) return (
    <div className="min-h-screen bg-brand-bg dark:bg-slate-900 flex items-center justify-center p-8">
      <p className="text-brand-text/60 text-center">Nenhum bloco disponível para esta missa.</p>
    </div>
  )

  return (
    <div className="reading-wide min-h-[100svh] bg-brand-bg dark:bg-slate-900 pb-40">
      <AppHeader
        title=""
        onBack={onBack}
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
              title="Índice de blocos"
              className="p-2 text-brand-text dark:text-slate-100 active:scale-90 transition-transform"
            >
              <ListIcon size={24} />
            </button>
          </div>
        }
      />

      {/* Referência da missa */}
      {missaData && (
        <div className="ds-container pt-3 pb-1">
          <div className="border-l-4 border-brand-gold pl-3">
            <div className="flex items-center flex-wrap gap-2 mb-1">
              <span className="ds-pill ds-pill-gold">
                {new Date(missaData + 'T12:00:00').toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' }).toUpperCase()}
              </span>
              {missaCor && (
                <span className="ds-section-label">Cor: {missaCor}</span>
              )}
            </div>
            {missaTitulo && (
              <h1 className="ds-headline text-brand-blue dark:text-brand-white break-words">
                {missaTitulo}
              </h1>
            )}
            {(missaCategoria || missaObservacoes) && (() => {
              const textoCompleto = [missaCategoria, missaObservacoes].filter(Boolean).join(' · ')
              const ehLongo = textoCompleto.length > 120
              return (
                <div className="mt-1">
                  <p
                    className="ds-body-sm font-serif italic text-brand-slate dark:text-gray-300 break-words"
                    style={ehLongo && !descricaoExpandida ? {
                      overflow: 'hidden',
                      display: '-webkit-box',
                      WebkitBoxOrient: 'vertical',
                      WebkitLineClamp: 2,
                      textOverflow: 'ellipsis',
                    } : {}}
                  >
                    {textoCompleto}
                  </p>
                  {ehLongo && (
                    <button
                      onClick={() => setDescricaoExpandida(!descricaoExpandida)}
                      className="ds-caption font-bold text-brand-gold mt-0.5 hover:opacity-80 active:scale-95 transition-transform"
                    >
                      {descricaoExpandida ? '↑ Ver menos' : '↓ Ver mais'}
                    </button>
                  )}
                </div>
              )
            })()}
          </div>
        </div>
      )}

      {/* Texto introdutório da missa (descrição) — só no primeiro bloco, com accordion */}
      {missaDescricao && currentIndex === 0 && (
        <div className="ds-container pt-2">
          <div className="ds-card-subtle">
            <p
              className="ds-body-sm font-serif italic text-brand-slate dark:text-gray-300 whitespace-pre-line"
              style={!descricaoExpandida ? {
                overflow: 'hidden',
                display: '-webkit-box',
                WebkitBoxOrient: 'vertical',
                WebkitLineClamp: 2,
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

      {/* Progress bar */}
      <div className="ds-container pt-3 pb-2">
        <div className="flex items-center gap-3">
          <div className="flex-1 h-2 bg-gray-200 dark:bg-slate-800 rounded-full overflow-hidden">
            <motion.div
              className="h-full bg-brand-gold"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.4 }}
            />
          </div>
          <span className="ds-caption text-gray-500 dark:text-gray-400 whitespace-nowrap">
            {currentIndex + 1} / {blocos.length}
          </span>
        </div>
      </div>

      {/* Content — scroll natural, sem container interno */}
      <div ref={contentRef} className="ds-container pt-4" id="reading-content">
        <AnimatePresence mode="wait">
          <motion.div
            key={currentIndex}
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -16 }}
            transition={{ duration: 0.25 }}
          >
            {/* Cabeçalho da seção (ex: LITURGIA DA PALAVRA) + descrição L. introdutória.
                A descrição vem AGRUPADA com o label da seção pra deixar claro que pertence
                à seção como um todo — não ao primeiro bloco (ex: Primeira Leitura). */}
            {secaoAtual && (
              <div className="mb-3 pb-3 border-b border-brand-gold/15">
                <p className="ds-section-label mb-2">
                  {secaoAtual.titulo}
                </p>
                {secaoAtual.primeiraOcorrencia && secaoAtual.descricao && (
                  <p className="ds-body-sm font-serif italic text-brand-slate dark:text-gray-300">
                    {secaoAtual.descricao}
                  </p>
                )}
              </div>
            )}

            {/* Apêndice (Leituras da Semana etc.): banner explicativo de que é
                conteúdo agregado, não parte da liturgia da celebração */}
            {currentBlock._ehApendice && (
              <div className="ds-card-subtle mb-3 flex items-start gap-2">
                <span className="ds-section-label text-brand-gold whitespace-nowrap mt-0.5">
                  Conteúdo Complementar
                </span>
                <span className="ds-body-sm font-serif italic text-brand-slate dark:text-gray-300">
                  · para aprofundar com base na liturgia
                </span>
              </div>
            )}

            <div className="flex items-start justify-between gap-3 mb-3">
              <div className="border-l-4 border-brand-gold pl-3 flex-1 min-w-0">
                <h2 className="ds-headline text-brand-text dark:text-slate-100 break-words">
                  {currentBlock._ehApendice
                    ? currentBlock.titulo
                    : `${currentBlock.numero_folheto ?? (currentIndex + 1)}. ${currentBlock.titulo}`}
                </h2>
                {currentBlock.introducao && (
                  <p className="ds-body-sm font-serif italic text-brand-slate dark:text-gray-300 mt-0.5">
                    {currentBlock.introducao}
                  </p>
                )}
                {currentBlock.subtitulo && (
                  <p className="ds-body-sm font-serif italic text-brand-slate dark:text-gray-300 mt-0.5">
                    {currentBlock.subtitulo}
                  </p>
                )}
                {currentBlock.referencia && (
                  <span className="ds-caption italic font-serif text-brand-slate dark:text-gray-400 block mt-0.5">
                    {currentBlock.referencia}
                  </span>
                )}
              </div>
              {currentBlock.postura && (
                <span className="ds-pill ds-pill-ghost flex-shrink-0 mt-1">
                  {currentBlock.postura === 'de_pe' ? 'De pé' : currentBlock.postura === 'sentado' ? 'Sentado' : currentBlock.postura === 'ajoelhado' ? 'Ajoelhado' : currentBlock.postura}
                </span>
              )}
            </div>

            {/* Conteúdo do bloco SEM caixa: o texto encosta na margem (alinhado
                à linha dourada do título) e usa a largura cheia. O recuo interno
                horizontal dos blocos é zerado via #reading-content .px-4 no CSS. */}
            <div className="reading-block">
              <BlocoRenderer bloco={currentBlock} />
              {/* Antífonas Entrada/Comunhão anexadas — renderizadas como aditivo
                  do bloco corrente (não geraram slide próprio). */}
              {currentBlock.antifonas_anexadas?.map((a: any, i: number) => (
                <div key={`ant-${i}`} className="px-4 py-3 mt-2 border-t border-brand-gold/20">
                  <p className="ds-section-label text-brand-gold mb-1">{a.titulo}</p>
                  {a.referencia && (
                    <p className="ds-caption italic font-serif text-brand-slate dark:text-gray-400 mb-1">
                      ({a.referencia})
                    </p>
                  )}
                  <p className="ds-body italic text-slate-700 dark:text-slate-300 whitespace-pre-line">
                    {a.texto}
                  </p>
                </div>
              ))}
            </div>
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Navigation buttons — FIXED no viewport (não rola junto com o conteúdo).
          padding-bottom alto pra ficar acima da barra inferior do Safari iOS quando ela aparece. */}
      <div
        className="fixed bottom-0 left-0 right-0 z-30 bg-brand-bg/95 dark:bg-slate-900/95 backdrop-blur-sm px-3 pt-2 border-t border-black/[0.06] dark:border-white/[0.06]"
        style={{ paddingBottom: 'calc(env(safe-area-inset-bottom) + 1rem)' }}
      >
        <div className="max-w-xl mx-auto flex gap-2">
          <button
            onClick={prevBlock}
            disabled={currentIndex === 0}
            className="flex-1 min-w-0 flex items-center justify-center gap-1.5 px-3 py-3 rounded-2xl bg-white dark:bg-slate-800 border-2 border-brand-blue/30 text-brand-blue dark:text-brand-gold dark:border-brand-gold/30 font-black text-sm active:scale-95 transition-transform disabled:opacity-40 disabled:cursor-not-allowed shadow-soft"
          >
            <ChevronLeft size={18} className="flex-shrink-0" />
            <span className="truncate">Anterior</span>
          </button>
          <button
            onClick={nextBlock}
            className={`flex-1 min-w-0 flex items-center justify-center gap-1.5 px-3 py-3 rounded-2xl font-black text-sm active:scale-95 transition-transform shadow-soft ${
              isLastBlock
                ? 'bg-brand-gold text-white shadow-strong'
                : 'bg-brand-blue text-white'
            }`}
          >
            <span className="truncate">{isLastBlock ? "Concluir" : "Próximo"}</span>
            {isLastBlock ? <Check size={18} className="flex-shrink-0" /> : <ChevronRight size={18} className="flex-shrink-0" />}
          </button>
        </div>
      </div>

      {/* Index Modal */}
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
                          currentIndex === idx
                            ? 'bg-brand-blue text-white shadow-md'
                            : 'bg-gray-50 dark:bg-slate-700/50 hover:bg-gray-100 dark:hover:bg-slate-700'
                        }`}
                      >
                        <div className={`w-10 h-10 rounded-full flex items-center justify-center font-bold text-sm ${
                          currentIndex === idx ? 'bg-white text-brand-blue' : 'bg-gray-200 dark:bg-slate-600 text-gray-500'
                        }`}>
                          {idx + 1}
                        </div>
                        <div className="flex-1">
                          <p className="font-bold leading-tight">{block.titulo}</p>
                          <p className="text-xs uppercase tracking-wider opacity-70">{block.tipo.replace(/_/g, ' ')}</p>
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

      {/* Modal: confirmação de reiniciar missa */}
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
              <h3 className="text-xl font-serif font-black text-brand-blue dark:text-brand-white text-center mb-2">
                Reiniciar missa?
              </h3>
              <p className="text-sm text-brand-gray-dark/70 dark:text-brand-white/70 text-center mb-6">
                Você voltará pro primeiro bloco e seu progresso será apagado. Local da missa e marcação de concluída também serão resetados.
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
                    // Backend: zera percentual no histórico (idempotente)
                    if (missaId) {
                      import('../services/api').then(({ default: api }) => {
                        api.post(`/usuarios/me/historico/${missaId}/desconcluir`).catch(() => { })
                      })
                    }
                    // Volta pro topo
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
