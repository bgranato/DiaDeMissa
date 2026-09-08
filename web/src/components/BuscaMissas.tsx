import { useEffect, useState } from 'react'
import { Search, X, ArrowRight } from 'lucide-react'
import api from '../services/api'

export interface MissaBusca {
  id: number
  data: string
  celebracao: string
  categoria: string | null
  observacoes: string | null
  total_blocos: number
  fonte_arqrio: boolean
  status: string
}

interface Props {
  setScreen: (s: string) => void
  defaultApenasArqrio?: boolean
  defaultDias?: number
  titulo?: string
}

/**
 * Busca por missas passadas. Carrega top resultados ao abrir (sem filtro).
 * Conforme o usuário digita, debounceia 400ms e refaz a busca.
 * Clique num resultado seta `@missa_data_alvo` no localStorage e navega pro Reading.
 */
export function BuscaMissas({
  setScreen,
  defaultApenasArqrio = true,
  defaultDias = 365,
  titulo = 'Buscar missas anteriores',
}: Props) {
  const [query, setQuery] = useState('')
  const [apenasArqrio, setApenasArqrio] = useState(defaultApenasArqrio)
  const [resultados, setResultados] = useState<MissaBusca[]>([])
  const [buscando, setBuscando] = useState(false)
  const [jaBuscou, setJaBuscou] = useState(false)

  // Só busca após 4+ caracteres pra não retornar listas longas demais.
  const MIN_CHARS = 4
  useEffect(() => {
    const q = query.trim()
    if (q.length < MIN_CHARS) {
      setResultados([])
      setJaBuscou(false)
      return
    }
    const handle = setTimeout(async () => {
      setBuscando(true)
      try {
        const r = await api.get<MissaBusca[]>('/missas/buscar', {
          params: { q, apenas_arqrio: apenasArqrio, dias: defaultDias },
        })
        setResultados(r.data)
        setJaBuscou(true)
      } finally {
        setBuscando(false)
      }
    }, 400)
    return () => clearTimeout(handle)
  }, [query, apenasArqrio, defaultDias])

  function abrirMissa(data: string) {
    localStorage.setItem('@missa_data_alvo', data)
    setScreen('reading')
  }

  return (
    <div className="ds-card">
      <div className="flex items-center gap-2 mb-3">
        <Search size={16} className="text-brand-gold" />
        <p className="ds-section-label">{titulo}</p>
      </div>
      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={e => setQuery(e.target.value)}
          placeholder="Data (dd/mm/aaaa) ou parte do título…"
          className="w-full px-4 py-2.5 pr-10 rounded-2xl bg-white dark:bg-slate-800 border-2 border-brand-blue/20 dark:border-brand-gold/20 text-sm font-medium text-brand-text dark:text-brand-white focus:outline-none focus:border-brand-blue dark:focus:border-brand-gold"
        />
        {query && (
          <button
            onClick={() => setQuery('')}
            className="absolute right-3 top-1/2 -translate-y-1/2 text-brand-gray-dark/60 hover:text-brand-gray-dark"
            aria-label="Limpar busca"
          >
            <X size={16} />
          </button>
        )}
      </div>
      <label className="flex items-center gap-2 mt-2 ds-caption text-brand-gray-dark/70 dark:text-brand-white/70">
        <input
          type="checkbox"
          checked={apenasArqrio}
          onChange={e => setApenasArqrio(e.target.checked)}
          className="rounded"
        />
        Somente folheto Arquidiocese (domingos/solenidades)
      </label>

      {buscando && (
        <div className="text-center py-4">
          <div className="w-6 h-6 border-2 border-brand-gold border-t-transparent rounded-full animate-spin mx-auto" />
        </div>
      )}

      {!buscando && query.trim().length > 0 && query.trim().length < MIN_CHARS && (
        <p className="text-center py-3 text-xs text-brand-gray-dark/50 dark:text-brand-white/50">
          Digite mais {MIN_CHARS - query.trim().length} caracter{MIN_CHARS - query.trim().length === 1 ? '' : 'es'} pra buscar…
        </p>
      )}

      {!buscando && jaBuscou && resultados.length === 0 && (
        <p className="text-center py-4 text-xs text-brand-gray-dark/60 dark:text-brand-white/60">
          Nenhuma missa encontrada para "{query.trim()}"
        </p>
      )}

      {!buscando && resultados.length > 0 && (
        <div className="mt-3 flex flex-col gap-2">
          <p className="ds-caption text-brand-gray-dark/60 dark:text-brand-white/60">
            {resultados.length} resultado{resultados.length === 1 ? '' : 's'}
          </p>
          {resultados.map(m => (
            <button
              key={m.id}
              onClick={() => abrirMissa(m.data)}
              className="flex items-center justify-between gap-3 p-3 rounded-xl bg-gray-50 dark:bg-slate-800/50 hover:bg-brand-blue/5 dark:hover:bg-brand-gold/5 active:scale-[0.99] transition-all text-left"
            >
              <div className="flex-1 min-w-0">
                <p className="text-xs font-bold text-brand-gold uppercase tracking-wider">
                  {new Date(m.data + 'T12:00:00').toLocaleDateString('pt-BR', {
                    weekday: 'short', day: 'numeric', month: 'short', year: 'numeric',
                  })}
                </p>
                <p className="text-sm font-bold text-brand-blue dark:text-brand-white truncate">
                  {m.celebracao || 'Missa'}
                </p>
                {(m.categoria || m.fonte_arqrio) && (
                  <p className="text-xs text-brand-gray-dark/70 dark:text-brand-white/70 truncate">
                    {[m.categoria, m.fonte_arqrio ? 'Arquidiocese' : null, `${m.total_blocos} blocos`]
                      .filter(Boolean)
                      .join(' · ')}
                  </p>
                )}
              </div>
              <ArrowRight size={16} className="text-brand-gold flex-shrink-0" />
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
