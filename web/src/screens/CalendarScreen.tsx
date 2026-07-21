import { useEffect, useState, useCallback, useRef } from 'react'
import { motion } from 'motion/react'
import { AppHeader, Card } from '../components/UI'
import { BuscaMissas } from '../components/BuscaMissas'
import { CheckCircle2, Clock, Play, BellPlus, Check, Hourglass } from 'lucide-react'
import api from '../services/api'

interface Props { setScreen: (s: string) => void }

interface MissaAgenda {
  id?: number
  data: string
  celebracao: string | null
  categoria?: string | null
  montada?: boolean
}
interface Agenda {
  anteriores: MissaAgenda[]
  proxima: MissaAgenda | null
}

function statusLocal(data: string): 'concluida' | 'em_progresso' | 'nao_iniciada' {
  if (localStorage.getItem(`@missa_concluida_${data}`) === 'true') return 'concluida'
  if (localStorage.getItem(`@missa_iniciada_${data}`) === 'true') return 'em_progresso'
  return 'nao_iniciada'
}

function partesData(data: string) {
  const d = new Date(data + 'T12:00:00')
  return {
    dia: d.getDate(),
    mes: d.toLocaleDateString('pt-BR', { month: 'short' }).replace('.', ''),
    diaSemana: d.toLocaleDateString('pt-BR', { weekday: 'long' }),
  }
}

export const CalendarScreen = ({ setScreen }: Props) => {
  const [agenda, setAgenda] = useState<Agenda | null>(null)
  const [loading, setLoading] = useState(true)
  const [lembretesAdicionados, setLembretesAdicionados] = useState<Set<string>>(new Set())
  const [lembreteEmCriacao, setLembreteEmCriacao] = useState<string | null>(null)
  const primeiraCarga = useRef(true)

  const carregar = useCallback(async () => {
    try {
      const r = await api.get<Agenda>('/missa/agenda')
      setAgenda(r.data)
    } catch {
      /* mantém o que tinha */
    } finally {
      if (primeiraCarga.current) { setLoading(false); primeiraCarga.current = false }
    }
  }, [])

  // Auto-atualização: recarrega ao abrir, a cada 60s e quando a aba volta ao foco.
  // Assim, quando a próxima missa for montada, o card "em breve" vira o card real.
  useEffect(() => {
    carregar()
    const id = setInterval(carregar, 60000)
    const onVis = () => { if (document.visibilityState === 'visible') carregar() }
    document.addEventListener('visibilitychange', onVis)
    return () => { clearInterval(id); document.removeEventListener('visibilitychange', onVis) }
  }, [carregar])

  function abrirMissa(data: string) {
    localStorage.setItem('@missa_data_alvo', data)
    setScreen('reading')
  }

  async function adicionarLembrete(m: MissaAgenda) {
    if (!m.id || lembretesAdicionados.has(m.data)) return
    setLembreteEmCriacao(m.data)
    try {
      const dataAlerta = new Date(m.data + 'T08:00:00')
      await api.post('/usuarios/me/lembretes', {
        missa_id: m.id,
        titulo: m.celebracao || 'Missa',
        nota: `Não esqueça da missa: ${m.celebracao || 'Missa'}`,
        data_hora_alerta: dataAlerta.toISOString(),
        minutos_antecedencia: 30,
        tipo: 'usuario',
      })
      setLembretesAdicionados(prev => new Set(prev).add(m.data))
    } catch {
      alert('Não foi possível adicionar o lembrete agora.')
    } finally {
      setLembreteEmCriacao(null)
    }
  }

  function CardMissa({ m, proxima }: { m: MissaAgenda; proxima?: boolean }) {
    const { dia, mes, diaSemana } = partesData(m.data)
    const status = statusLocal(m.data)
    const lembreteOK = lembretesAdicionados.has(m.data)
    const lembreteCarregando = lembreteEmCriacao === m.data
    return (
      <Card className={proxima ? 'ds-card-feature' : ''}>
        <div className="flex items-start gap-4">
          <div className="text-center min-w-[52px] flex-shrink-0">
            <div className="ds-section-label">{mes}</div>
            <div className={`text-2xl font-black leading-none mt-0.5 ${proxima ? 'text-brand-gold' : 'text-brand-blue dark:text-white'}`}>{dia}</div>
            <div className="text-[10px] font-bold text-brand-gray-dark/60 dark:text-brand-white/60 uppercase mt-1">{diaSemana.slice(0, 3)}</div>
          </div>
          <div className="flex-1 min-w-0">
            {proxima && <span className="ds-section-label block mb-1">Próxima missa</span>}
            <p className="ds-title text-brand-gray-dark dark:text-brand-white break-words">{m.celebracao || 'Missa'}</p>
            <p className="ds-caption text-brand-gray-dark/60 dark:text-brand-white/60 capitalize mt-0.5">{diaSemana}</p>
          </div>
          {status === 'concluida' && <CheckCircle2 size={20} className="text-green-500 flex-shrink-0 mt-1" />}
          {status === 'em_progresso' && <Clock size={20} className="text-brand-gold flex-shrink-0 mt-1" />}
        </div>
        <div className="flex items-center gap-2 mt-4 pt-3 border-t border-black/5 dark:border-white/5">
          <button onClick={() => abrirMissa(m.data)} className="ds-btn ds-btn-primary flex-1 min-w-0">
            <Play size={16} /><span className="truncate">Acompanhar</span>
          </button>
          {proxima && (
            <button onClick={() => adicionarLembrete(m)} disabled={lembreteOK || lembreteCarregando}
              title={lembreteOK ? 'Lembrete já adicionado' : 'Adicionar lembrete'}
              className={`ds-btn flex-shrink-0 ${lembreteOK ? 'ds-btn-secondary' : 'ds-btn-outline'}`}>
              {lembreteOK ? <Check size={16} /> : <BellPlus size={16} />}
              <span className="hidden sm:inline">{lembreteOK ? 'Adicionado' : 'Lembrete'}</span>
            </button>
          )}
        </div>
      </Card>
    )
  }

  function CardProximaEmBreve({ m }: { m: MissaAgenda }) {
    const { dia, mes, diaSemana } = partesData(m.data)
    return (
      <Card className="ds-card-feature">
        <div className="flex items-start gap-4">
          <div className="text-center min-w-[52px] flex-shrink-0">
            <div className="ds-section-label">{mes}</div>
            <div className="text-2xl font-black leading-none mt-0.5 text-brand-gold">{dia}</div>
            <div className="text-[10px] font-bold text-brand-gray-dark/60 dark:text-brand-white/60 uppercase mt-1">{diaSemana.slice(0, 3)}</div>
          </div>
          <div className="flex-1 min-w-0">
            <span className="ds-section-label block mb-1">Próxima missa</span>
            <p className="ds-title text-brand-gray-dark dark:text-brand-white capitalize break-words">{diaSemana}</p>
            <p className="ds-body-sm font-serif italic text-brand-slate dark:text-gray-300 mt-1">
              Assim que o folheto for publicado, a missa aparece aqui automaticamente.
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 mt-4 pt-3 border-t border-black/5 dark:border-white/5 text-brand-slate dark:text-gray-400">
          <Hourglass size={16} className="text-brand-gold" />
          <span className="ds-caption">Aguardando publicação</span>
        </div>
      </Card>
    )
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      className="min-h-screen bg-brand-bg dark:bg-slate-900 ds-bottom-nav-padding">
      <AppHeader title="Agenda" onBack={() => setScreen('home')} />

      <div className="ds-container mt-6 ds-stack-md">
        <BuscaMissas setScreen={setScreen} titulo="Buscar missa por data ou título" />

        {loading && (
          <div className="text-center py-10">
            <div className="w-8 h-8 border-4 border-brand-gold border-t-transparent rounded-full animate-spin mx-auto" />
          </div>
        )}

        {!loading && agenda && (
          <>
            {agenda.proxima && (
              <div className="ds-stack-md">
                <p className="ds-section-label mt-2 px-1">Próxima</p>
                {agenda.proxima.montada
                  ? <CardMissa m={agenda.proxima} proxima />
                  : <CardProximaEmBreve m={agenda.proxima} />}
              </div>
            )}

            {agenda.anteriores.length > 0 && (
              <div className="ds-stack-md">
                <p className="ds-section-label mt-2 px-1">Últimas missas</p>
                {agenda.anteriores.map(m => <CardMissa key={m.data} m={m} />)}
              </div>
            )}

            {agenda.anteriores.length === 0 && !agenda.proxima && (
              <div className="text-center py-10 px-6">
                <p className="ds-body text-brand-gray-dark/60 dark:text-brand-white/60">Nenhuma missa disponível.</p>
                <p className="ds-body-sm text-brand-gray-dark/40 italic mt-1">Use a busca acima para encontrar missas anteriores.</p>
              </div>
            )}
          </>
        )}
      </div>
    </motion.div>
  )
}
