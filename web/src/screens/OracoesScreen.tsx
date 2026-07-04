import { useState, useEffect, useRef } from 'react'
import { motion, AnimatePresence } from 'motion/react'
import { AppHeader, Card, PrayingHandsIcon } from '../components/UI'
import { ChevronRight, Play, Pause, Volume2, Settings2, Search, X } from 'lucide-react'
import { CATEGORIAS, ORACOES, ORACOES_POR_CATEGORIA, type Oracao } from '../data/oracoes'

function normalizar(s: string): string {
  // Lowercase + remove diacríticos (Á → a, ç → c, etc.) — busca tolerante a acentos
  return s.toLowerCase().normalize('NFKD').replace(/[̀-ͯ]/g, '')
}

interface Props {
  setScreen: (s: string) => void
}

/**
 * Escolhe a melhor voz pt-BR disponível no sistema.
 * Prioridade: Google neural > Microsoft > Apple > qualquer pt-BR > qualquer pt.
 */
function escolherMelhorVoz(vozes: SpeechSynthesisVoice[]): SpeechSynthesisVoice | undefined {
  const pt = vozes.filter(v => v.lang.toLowerCase().startsWith('pt'))
  if (pt.length === 0) return undefined

  const prefs: ((v: SpeechSynthesisVoice) => boolean)[] = [
    // Google neural (Chrome) — geralmente a melhor qualidade
    v => /google/i.test(v.name) && v.lang === 'pt-BR',
    v => /google/i.test(v.name) && v.lang.startsWith('pt'),
    // Microsoft Edge / Windows — vozes "Online (Natural)" são neurais
    v => /natural/i.test(v.name) && v.lang === 'pt-BR',
    v => /microsoft/i.test(v.name) && v.lang === 'pt-BR',
    // Apple — Luciana/Felipe têm qualidade aceitável
    v => /luciana|felipe/i.test(v.name),
    // Qualquer pt-BR
    v => v.lang === 'pt-BR',
    // Qualquer pt
    () => true,
  ]
  for (const pref of prefs) {
    const found = pt.find(pref)
    if (found) return found
  }
  return pt[0]
}

const STORAGE_VOZ = '@tts_voz_preferida'

export const OracoesScreen = ({ setScreen }: Props) => {
  const [oracaoAtiva, setOracaoAtiva] = useState<Oracao | null>(null)
  const [busca, setBusca] = useState('')
  const [falando, setFalando] = useState(false)
  const [vozesDisponiveis, setVozesDisponiveis] = useState<SpeechSynthesisVoice[]>([])
  const [vozEscolhida, setVozEscolhida] = useState<string>(localStorage.getItem(STORAGE_VOZ) || '')
  const [showConfig, setShowConfig] = useState(false)
  const utteranceRef = useRef<SpeechSynthesisUtterance | null>(null)

  // Sempre que abrir uma oração, rola pro topo da página
  useEffect(() => {
    if (oracaoAtiva) {
      window.scrollTo({ top: 0, behavior: 'auto' })
    }
  }, [oracaoAtiva?.id])

  // Filtra orações pela busca (nome, texto, observação) — case e accent-insensitive
  const termoBusca = normalizar(busca.trim())
  const resultados: Oracao[] = termoBusca
    ? ORACOES.filter(o => {
        const haystack = normalizar(`${o.nome} ${o.texto} ${o.observacao || ''}`)
        return haystack.includes(termoBusca)
      })
    : []

  // Carrega vozes disponíveis (algumas plataformas carregam async)
  useEffect(() => {
    const sync = window.speechSynthesis
    if (!sync) return
    const carregar = () => {
      const vozes = sync.getVoices().filter(v => v.lang.toLowerCase().startsWith('pt'))
      setVozesDisponiveis(vozes)
    }
    carregar()
    sync.addEventListener?.('voiceschanged', carregar)
    return () => sync.removeEventListener?.('voiceschanged', carregar)
  }, [])

  useEffect(() => {
    return () => { window.speechSynthesis.cancel() }
  }, [])

  useEffect(() => {
    window.speechSynthesis.cancel()
    setFalando(false)
  }, [oracaoAtiva?.id])

  function falar(texto: string) {
    if (typeof window === 'undefined' || !window.speechSynthesis) {
      alert('Seu navegador não suporta leitura de voz.')
      return
    }
    window.speechSynthesis.cancel()

    const u = new SpeechSynthesisUtterance(texto)
    u.lang = 'pt-BR'
    u.rate = 0.95   // levemente mais devagar (mais natural pra oração)
    u.pitch = 1.0
    u.volume = 1.0

    const vozes = window.speechSynthesis.getVoices()
    let voz: SpeechSynthesisVoice | undefined
    if (vozEscolhida) {
      voz = vozes.find(v => v.name === vozEscolhida)
    }
    if (!voz) voz = escolherMelhorVoz(vozes)
    if (voz) u.voice = voz

    u.onend = () => setFalando(false)
    u.onerror = () => setFalando(false)
    utteranceRef.current = u
    setFalando(true)
    window.speechSynthesis.speak(u)
  }

  function trocarVoz(nome: string) {
    setVozEscolhida(nome)
    if (nome) localStorage.setItem(STORAGE_VOZ, nome)
    else localStorage.removeItem(STORAGE_VOZ)
  }

  function pararFala() {
    window.speechSynthesis.cancel()
    setFalando(false)
  }

  // Vista de DETALHE (oração selecionada)
  if (oracaoAtiva) {
    return (
      <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }}
        className="min-h-screen bg-brand-bg dark:bg-slate-900 ds-bottom-nav-padding">
        <AppHeader title="Oração" onBack={() => setOracaoAtiva(null)} />

        <div className="max-w-lg mx-auto px-5 mt-6 flex flex-col gap-5">
          <div className="text-center">
            <div className="text-brand-gold mb-3 flex justify-center"><PrayingHandsIcon size={32} /></div>
            <h2 className="text-2xl font-serif font-black text-brand-blue dark:text-brand-white leading-tight">
              {oracaoAtiva.nome}
            </h2>
            <span className="inline-block mt-2 text-[10px] font-black text-brand-gold uppercase tracking-[0.3em]">
              {CATEGORIAS.find(c => c.id === oracaoAtiva.categoria)?.nome}
            </span>
          </div>

          {/* Botão de leitura assistida + config de voz */}
          <div className="flex items-center gap-2">
            <button
              onClick={() => (falando ? pararFala() : falar(oracaoAtiva.texto))}
              className={`flex-1 flex items-center justify-center gap-3 h-14 rounded-2xl font-black text-sm uppercase tracking-wider transition-all active:scale-[0.98] ${
                falando
                  ? 'bg-red-500 text-white shadow-strong'
                  : 'bg-brand-blue text-white dark:bg-brand-gold dark:text-brand-blue shadow-soft'
              }`}
            >
              {falando ? <Pause size={20} /> : <Play size={20} />}
              {falando ? 'Parar leitura' : 'Ouvir oração'}
              {!falando && <Volume2 size={18} className="opacity-70" />}
            </button>
            {vozesDisponiveis.length > 1 && (
              <button
                onClick={() => setShowConfig(!showConfig)}
                title="Trocar voz"
                className="h-14 w-14 rounded-2xl bg-brand-white dark:bg-slate-800 shadow-soft border border-black/[0.05] dark:border-slate-700 flex items-center justify-center text-brand-blue dark:text-brand-gold active:scale-95 transition-transform"
              >
                <Settings2 size={20} />
              </button>
            )}
          </div>

          {/* Painel de configuração de voz */}
          <AnimatePresence>
            {showConfig && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="overflow-hidden"
              >
                <Card className="p-4 bg-brand-blue/5 dark:bg-brand-gold/5">
                  <p className="text-[10px] font-black text-brand-gold uppercase tracking-[0.3em] mb-2">Voz da leitura</p>
                  <select
                    value={vozEscolhida}
                    onChange={e => trocarVoz(e.target.value)}
                    className="w-full bg-white dark:bg-slate-900 border border-black/10 dark:border-slate-700 rounded-xl px-3 py-2 text-sm font-medium"
                  >
                    <option value="">Automática (melhor disponível)</option>
                    {vozesDisponiveis.map(v => (
                      <option key={v.name} value={v.name}>
                        {v.name} ({v.lang}){v.localService ? '' : ' • online'}
                      </option>
                    ))}
                  </select>
                  <p className="text-xs text-brand-gray-dark/50 dark:text-brand-white/50 mt-2">
                    {vozesDisponiveis.length} vozes em português detectadas. Vozes "Google" e "Natural" geralmente soam melhor.
                  </p>
                </Card>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Texto da oração SEM caixa — respira na largura da tela, como a liturgia. */}
          <div className="px-1 pt-2">
            <p className="font-serif text-lg leading-[1.8] text-brand-gray-dark dark:text-brand-white whitespace-pre-line">
              {oracaoAtiva.texto}
            </p>
          </div>

          {oracaoAtiva.observacao && (
            <Card className="p-5 bg-brand-gold/10 border border-brand-gold/20">
              <p className="text-xs italic text-brand-gray-dark/70 dark:text-brand-white/70 leading-relaxed">
                {oracaoAtiva.observacao}
              </p>
            </Card>
          )}
        </div>
      </motion.div>
    )
  }

  // Vista de LISTA
  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      className="min-h-screen bg-brand-bg dark:bg-slate-900 ds-bottom-nav-padding">
      <AppHeader title="Orações" onBack={() => setScreen('home')} />

      <div className="max-w-lg mx-auto px-5 mt-6 flex flex-col gap-6">
        {/* Busca por nome, palavra ou trecho */}
        <div className="flex items-center gap-2 bg-brand-white dark:bg-slate-800 rounded-2xl pl-5 pr-2 py-2 border border-black/5 dark:border-slate-700 shadow-soft">
          <Search size={20} className="text-brand-gold flex-shrink-0" />
          <input
            value={busca}
            onChange={e => setBusca(e.target.value)}
            placeholder="Buscar por nome, palavra ou trecho..."
            className="bg-transparent w-full text-base font-medium outline-none placeholder:text-gray-400 dark:text-white"
          />
          {busca && (
            <button onClick={() => setBusca('')}
              title="Limpar"
              className="flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-brand-gray-dark/40 hover:bg-gray-100 dark:hover:bg-slate-700">
              <X size={16} />
            </button>
          )}
        </div>

        {/* Resultados da busca — exibidos no lugar das categorias */}
        {termoBusca && (
          <div className="flex flex-col gap-3">
            <div className="px-1">
              <h3 className="text-[10px] font-black text-brand-gold uppercase tracking-[0.3em]">
                Resultados ({resultados.length})
              </h3>
              {resultados.length === 0 && (
                <p className="text-xs text-brand-gray-dark/50 dark:text-brand-white/50 mt-2">
                  Nenhuma oração encontrada com "{busca}".
                </p>
              )}
            </div>
            <div className="flex flex-col gap-2">
              {resultados.map(o => (
                <button key={o.id} onClick={() => setOracaoAtiva(o)}
                  className="flex items-center gap-3 p-4 bg-brand-white dark:bg-slate-800 rounded-2xl shadow-soft border border-black/[0.03] dark:border-slate-700 active:scale-[0.98] transition-transform text-left">
                  <div className="p-2.5 bg-brand-gold/15 dark:bg-brand-gold/25 rounded-xl flex-shrink-0">
                    <span className="text-brand-gold"><PrayingHandsIcon size={18} /></span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-black text-brand-gray-dark dark:text-brand-white text-sm leading-tight">{o.nome}</p>
                    <p className="text-[10px] font-bold text-brand-gold uppercase tracking-wider mt-0.5">
                      {CATEGORIAS.find(c => c.id === o.categoria)?.nome}
                    </p>
                  </div>
                  <ChevronRight size={18} className="text-brand-gray-dark/40 dark:text-brand-white/40 flex-shrink-0" />
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Categorias — escondidas quando há busca ativa */}
        {!termoBusca && CATEGORIAS.map(cat => {
          const lista = ORACOES_POR_CATEGORIA[cat.id] || []
          if (lista.length === 0) return null
          return (
            <div key={cat.id} className="flex flex-col gap-3">
              <div className="px-1">
                <h3 className="text-[10px] font-black text-brand-gold uppercase tracking-[0.3em]">{cat.nome}</h3>
                <p className="text-xs text-brand-gray-dark/50 dark:text-brand-white/50 mt-1">{cat.descricao}</p>
              </div>
              <div className="flex flex-col gap-2">
                {lista.map(o => (
                  <button key={o.id} onClick={() => setOracaoAtiva(o)}
                    className="flex items-center gap-3 p-4 bg-brand-white dark:bg-slate-800 rounded-2xl shadow-soft border border-black/[0.03] dark:border-slate-700 active:scale-[0.98] transition-transform text-left">
                    <div className="p-2.5 bg-brand-gold/15 dark:bg-brand-gold/25 rounded-xl flex-shrink-0">
                      <span className="text-brand-gold"><PrayingHandsIcon size={18} /></span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-black text-brand-gray-dark dark:text-brand-white text-sm leading-tight">{o.nome}</p>
                    </div>
                    <ChevronRight size={18} className="text-brand-gray-dark/40 dark:text-brand-white/40 flex-shrink-0" />
                  </button>
                ))}
              </div>
            </div>
          )
        })}
      </div>
    </motion.div>
  )
}
