import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { AppHeader, LargeButton, Card } from '../components/UI'
import { useAccessibility } from '../hooks/useAccessibility'
import { getMissaAtual, salvarProgressoMissa, concluirMissa } from '../services/missa'
import { logError } from '../services/logger'
import BlocoRenderer from '../components/blocos/BlocoRenderer'
import { ChevronLeft, ChevronRight, List as ListIcon, X, Check } from 'lucide-react'

interface Props {
  onBack: () => void
  onFinish: () => void
  missaId?: number
}

interface SectionInfo {
  titulo: string
  descricao?: string | null
  primeiraOcorrencia: boolean
}

export const ReadingScreen = ({ onBack, onFinish, missaId }: Props) => {
  const [todosBlocos, setTodosBlocos] = useState<any[]>([])
  const [missaData, setMissaData] = useState<string | null>(null)
  const [currentIndex, setCurrentIndex] = useState(0)
  const [showIndex, setShowIndex] = useState(false)
  const [loading, setLoading] = useState(true)
  const contentRef = useRef<HTMLDivElement>(null)
  const { prefs } = useAccessibility()

  useEffect(() => {
    getMissaAtual()
      .then((missa: any) => {
        setTodosBlocos(missa.blocos || [])
        setMissaData(missa.data || null)
      })
      .catch(err => {
        console.error('Erro ao carregar missa:', err)
        setTodosBlocos([])
      })
      .finally(() => setLoading(false))
  }, [])

  // Marca a missa como "iniciada" só na primeira vez que o usuário avança
  // (currentIndex sai de 0). Apenas abrir a tela não conta como iniciar.
  const marcarIniciada = () => {
    if (missaData && localStorage.getItem(`@missa_concluida_${missaData}`) !== 'true') {
      localStorage.setItem(`@missa_iniciada_${missaData}`, 'true')
    }
  }

  // Separa seções (categorias master) dos blocos navegáveis.
  // Cada bloco navegável carrega referência à seção a que pertence; a primeira
  // ocorrência de cada seção mostra também a descrição (texto "L." introdutório).
  const { blocos, secaoPorIndice } = (() => {
    const list: any[] = []
    const sec: Record<number, SectionInfo> = {}
    let secaoAtual: { titulo: string; descricao?: string | null } | null = null
    let secaoJaUsada = new Set<string>()
    for (const b of todosBlocos) {
      if (b.tipo === 'secao') {
        secaoAtual = { titulo: b.titulo, descricao: b.descricao }
        continue
      }
      const idxNovo = list.length
      list.push(b)
      if (secaoAtual) {
        const primeira = !secaoJaUsada.has(secaoAtual.titulo)
        sec[idxNovo] = {
          titulo: secaoAtual.titulo,
          descricao: primeira ? secaoAtual.descricao : null,
          primeiraOcorrencia: primeira,
        }
        secaoJaUsada.add(secaoAtual.titulo)
      }
    }
    return { blocos: list, secaoPorIndice: sec }
  })()

  const currentBlock = blocos[currentIndex]
  const secaoAtual = secaoPorIndice[currentIndex]
  const isLastBlock = currentIndex === blocos.length - 1
  const progress = blocos.length > 0 ? Math.round(((currentIndex + 1) / blocos.length) * 100) : 0

  const scrollToTop = () => {
    if (contentRef.current) contentRef.current.scrollTo(0, 0)
  }

  const persistirProgresso = (index: number) => {
    if (!missaId || blocos.length === 0) return
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
    <div className="min-h-screen bg-brand-bg dark:bg-slate-900 flex flex-col">
      <AppHeader 
        title="" 
        onBack={onBack}
        rightElement={
          <button onClick={() => setShowIndex(true)} className="p-2 text-brand-text dark:text-slate-100">
            <ListIcon size={24} />
          </button>
        }
      />

      {/* Progress bar */}
      <div className="max-w-xl mx-auto w-full px-5 pt-4 pb-2">
        <div className="flex items-center gap-4">
          <div className="flex-1 h-3 bg-gray-200 dark:bg-slate-800 rounded-full overflow-hidden">
            <motion.div 
              className="h-full bg-brand-gold shadow-[0_0_10px_rgba(201,162,39,0.5)]"
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 0.5 }}
            />
          </div>
          <span className="text-sm font-bold text-gray-500 dark:text-gray-400 whitespace-nowrap">
            {currentIndex + 1} de {blocos.length}
          </span>
        </div>
      </div>

      {/* Content area with fade at bottom */}
      <div className="flex-1 relative overflow-hidden">
        <div ref={contentRef} className="absolute inset-0 overflow-y-auto px-5 pt-5 pb-40" id="reading-content">
          <div className="max-w-xl mx-auto">
            <AnimatePresence mode="wait">
              <motion.div
                key={currentIndex}
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
              >
                {/* Label master da seção, acima do título */}
                {secaoAtual && (
                  <p className="text-[10px] uppercase tracking-[0.4em] text-brand-gold font-black mb-2">
                    {secaoAtual.titulo}
                  </p>
                )}

                <div className="flex items-start justify-between gap-3 mb-4">
                  <div className="border-l-4 border-brand-gold pl-4 py-1 flex-1 min-w-0">
                    <h2 className="font-serif font-black leading-tight text-3xl text-brand-text dark:text-slate-100">
                      {currentIndex + 1}. {currentBlock.titulo}
                    </h2>
                    {currentBlock.introducao && (
                      <p className="text-base font-serif italic text-brand-slate dark:text-gray-300 mt-1">
                        {currentBlock.introducao}
                      </p>
                    )}
                    {currentBlock.subtitulo && (
                      <p className="text-base font-serif italic text-brand-slate dark:text-gray-300 mt-1">
                        {currentBlock.subtitulo}
                      </p>
                    )}
                    {currentBlock.referencia && (
                      <span className="text-sm italic font-serif text-brand-slate dark:text-gray-400 block mt-0.5">
                        {currentBlock.referencia}
                      </span>
                    )}
                  </div>
                  {currentBlock.postura && (
                    <span className="flex-shrink-0 px-3 py-1 bg-amber-50 text-amber-700 rounded-full text-xs font-bold uppercase tracking-wider mt-2">
                      {currentBlock.postura === 'de_pe' ? 'De pé' : currentBlock.postura === 'sentado' ? 'Sentado' : currentBlock.postura === 'ajoelhado' ? 'Ajoelhado' : currentBlock.postura}
                    </span>
                  )}
                </div>

                {/* Descrição introdutória da seção (L.) — só na primeira ocorrência */}
                {secaoAtual?.primeiraOcorrencia && secaoAtual.descricao && (
                  <div className="bg-brand-gold/5 border-l-4 border-brand-gold/40 rounded-r-lg px-4 py-3 mb-4">
                    <p className="text-sm font-serif italic text-brand-slate dark:text-gray-300 leading-relaxed">
                      {secaoAtual.descricao}
                    </p>
                  </div>
                )}

                <Card className="shadow-sm border-brand-gray dark:border-slate-800">
                  <BlocoRenderer bloco={currentBlock} />
                </Card>
              </motion.div>
            </AnimatePresence>
          </div>
        </div>

        {/* Gradient fade overlay */}
        <div className="absolute bottom-0 left-0 right-0 h-24 bg-gradient-to-t from-brand-bg via-brand-bg/90 to-transparent dark:from-slate-900 dark:via-slate-900/90 dark:to-transparent pointer-events-none z-10" />
      </div>

      {/* Navigation buttons - fixed at bottom */}
      <div className="sticky bottom-0 left-0 right-0 z-20 bg-brand-bg dark:bg-slate-900 px-5 pb-6 pt-2">
        <div className="max-w-xl mx-auto flex gap-3">
          <LargeButton 
            variant="outline" 
            onClick={prevBlock}
            disabled={currentIndex === 0}
            className="flex-1 bg-white dark:bg-slate-800"
            icon={ChevronLeft}
          >
            Anterior
          </LargeButton>
          <LargeButton 
            variant={isLastBlock ? "secondary" : "primary"} 
            onClick={nextBlock}
            className="flex-1"
            icon={isLastBlock ? Check : ChevronRight}
          >
            {isLastBlock ? "Concluir" : "Próximo"}
          </LargeButton>
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
    </div>
  )
}
