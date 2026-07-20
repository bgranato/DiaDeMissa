import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { AppHeader, Card } from '../components/UI'
import { BuscaMissas } from '../components/BuscaMissas'
import { getMissaPorData } from '../services/missa'
import { CheckCircle2, Clock, CircleDashed, Play, BellPlus, Check } from 'lucide-react'
import type { Missa } from '../types/missa'
import api from '../services/api'

interface Props { setScreen: (s: string) => void }

interface ItemAgenda {
  data: string  // YYYY-MM-DD
  missa: Missa | null
  ehHoje: boolean
  ehPassado: boolean
}

function formatarData(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function statusLocal(data: string): 'concluida' | 'em_progresso' | 'nao_iniciada' {
  if (localStorage.getItem(`@missa_concluida_${data}`) === 'true') return 'concluida'
  if (localStorage.getItem(`@missa_iniciada_${data}`) === 'true') return 'em_progresso'
  return 'nao_iniciada'
}

export const CalendarScreen = ({ setScreen }: Props) => {
  const [itens, setItens] = useState<ItemAgenda[]>([])
  const [loading, setLoading] = useState(true)
  // Datas que já têm lembrete adicionado nesta sessão (feedback visual)
  const [lembretesAdicionados, setLembretesAdicionados] = useState<Set<string>>(new Set())
  const [lembreteEmCriacao, setLembreteEmCriacao] = useState<string | null>(null)

  useEffect(() => {
    carregar()
  }, [])

  async function carregar() {
    setLoading(true)
    const hoje = new Date()
    hoje.setHours(12, 0, 0, 0)
    const hojeStr = formatarData(hoje)

    // 2 passadas + hoje + 4 futuras = 7 dias
    const datas: string[] = []
    for (let offset = -2; offset <= 4; offset++) {
      const d = new Date(hoje)
      d.setDate(hoje.getDate() + offset)
      datas.push(formatarData(d))
    }

    // Busca em paralelo (todas as datas)
    const respostas = await Promise.allSettled(datas.map(d => getMissaPorData(d)))

    const lista: ItemAgenda[] = datas.map((data, i) => ({
      data,
      missa: respostas[i].status === 'fulfilled' ? respostas[i].value : null,
      ehHoje: data === hojeStr,
      ehPassado: data < hojeStr,
    }))
    setItens(lista)
    setLoading(false)
  }

  function abrirMissa(data: string) {
    // ReadingScreen vai ler `@missa_data_alvo` do localStorage no useEffect
    localStorage.setItem('@missa_data_alvo', data)
    setScreen('reading')
  }

  async function adicionarLembrete(item: ItemAgenda) {
    if (!item.missa) return
    if (lembretesAdicionados.has(item.data)) return
    setLembreteEmCriacao(item.data)
    try {
      // Default: lembrete pra 8h da manhã do dia da missa, com 30min de antecedência
      const dataAlerta = new Date(item.data + 'T08:00:00')
      await api.post('/usuarios/me/lembretes', {
        missa_id: item.missa.id,
        titulo: item.missa.celebracao || 'Missa',
        nota: `Não esqueça da missa: ${item.missa.celebracao || 'Missa'}`,
        data_hora_alerta: dataAlerta.toISOString(),
        minutos_antecedencia: 30,
        tipo: 'usuario',
      })
      setLembretesAdicionados(prev => new Set(prev).add(item.data))
    } catch {
      alert('Não foi possível adicionar o lembrete agora.')
    } finally {
      setLembreteEmCriacao(null)
    }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}
      className="min-h-screen bg-brand-bg dark:bg-slate-900 ds-bottom-nav-padding">
      <AppHeader title="Agenda" onBack={() => setScreen('home')} />

      <div className="ds-container mt-6 ds-stack-md">
        {/* Busca por missas anteriores — primeiro na ordem visual */}
        <BuscaMissas setScreen={setScreen} titulo="Buscar missa por data ou título" />

        {loading && (
          <div className="text-center py-10">
            <div className="w-8 h-8 border-4 border-brand-gold border-t-transparent rounded-full animate-spin mx-auto" />
          </div>
        )}

        {(['Anteriores', 'Hoje e próximos dias'] as const).map(secao => {
          // Só entram dias que TÊM missa montada (com conteúdo). Dias sem missa
          // (feriados/dias de semana sem folheto) não aparecem no histórico.
          const grupo = itens.filter(i =>
            i.missa && (secao === 'Anteriores' ? i.ehPassado : !i.ehPassado))
          if (loading || grupo.length === 0) return null
          return (
            <div key={secao} className="ds-stack-md">
              <p className="ds-section-label mt-2 px-1">{secao}</p>
              {grupo.map(item => {
          const dataObj = new Date(item.data + 'T12:00:00')
          const diaSemana = dataObj.toLocaleDateString('pt-BR', { weekday: 'long' })
          const dia = dataObj.getDate()
          const mes = dataObj.toLocaleDateString('pt-BR', { month: 'short' }).replace('.', '')
          const status = statusLocal(item.data)
          const semMissa = !item.missa
          const lembreteOK = lembretesAdicionados.has(item.data)
          const lembreteCarregando = lembreteEmCriacao === item.data

          const cardClass = [
            item.ehHoje ? 'ds-card-feature' : '',
            item.ehPassado ? 'opacity-60' : '',
          ].filter(Boolean).join(' ')

          return (
            <Card key={item.data} className={cardClass}>
              {/* Linha info */}
              <div className="flex items-start gap-4">
                <div className={`text-center min-w-[52px] flex-shrink-0`}>
                  <div className="ds-section-label">{mes}</div>
                  <div className={`text-2xl font-black leading-none mt-0.5 ${item.ehHoje ? 'text-brand-gold' : 'text-brand-blue dark:text-white'}`}>
                    {dia}
                  </div>
                  <div className="text-[10px] font-bold text-brand-gray-dark/60 dark:text-brand-white/60 uppercase mt-1">
                    {diaSemana.slice(0, 3)}
                  </div>
                </div>

                <div className="flex-1 min-w-0">
                  {item.ehHoje && (
                    <span className="ds-section-label block mb-1">Hoje</span>
                  )}
                  {semMissa ? (
                    <p className="ds-body-sm text-brand-gray-dark/40 italic">Sem missa cadastrada</p>
                  ) : (
                    <>
                      <p className="ds-title text-brand-gray-dark dark:text-brand-white break-words">
                        {item.missa!.celebracao || 'Missa'}
                      </p>
                      <p className="ds-caption text-brand-gray-dark/60 dark:text-brand-white/60 capitalize mt-0.5">
                        {diaSemana}
                      </p>
                    </>
                  )}
                </div>

                {/* Status */}
                {!semMissa && (
                  <div className="flex-shrink-0">
                    {status === 'concluida' && <CheckCircle2 size={20} className="text-green-500" />}
                    {status === 'em_progresso' && <Clock size={20} className="text-brand-gold" />}
                    {status === 'nao_iniciada' && item.ehPassado && (
                      <CircleDashed size={20} className="text-brand-gray-dark/30" />
                    )}
                  </div>
                )}
              </div>

              {/* Ações — só pra missas existentes */}
              {!semMissa && (
                <div className="flex items-center gap-2 mt-4 pt-3 border-t border-black/5 dark:border-white/5">
                  <button
                    onClick={() => abrirMissa(item.data)}
                    className="ds-btn ds-btn-primary flex-1 min-w-0"
                  >
                    <Play size={16} />
                    <span className="truncate">Acompanhar</span>
                  </button>
                  <button
                    onClick={() => adicionarLembrete(item)}
                    disabled={lembreteOK || lembreteCarregando || item.ehPassado}
                    title={item.ehPassado ? 'Não há lembrete para datas passadas' : (lembreteOK ? 'Lembrete já adicionado' : 'Adicionar lembrete')}
                    className={`ds-btn flex-shrink-0 ${lembreteOK ? 'ds-btn-secondary' : 'ds-btn-outline'}`}
                  >
                    {lembreteOK ? <Check size={16} /> : <BellPlus size={16} />}
                    <span className="hidden sm:inline">{lembreteOK ? 'Adicionado' : 'Lembrete'}</span>
                  </button>
                </div>
              )}
            </Card>
          )
              })}
            </div>
          )
        })}

        {!loading && itens.every(i => !i.missa) && (
          <div className="text-center py-10 px-6">
            <p className="ds-body text-brand-gray-dark/60 dark:text-brand-white/60">
              Nenhuma missa nos próximos dias.
            </p>
            <p className="ds-body-sm text-brand-gray-dark/40 italic mt-1">
              Use a busca acima para encontrar missas anteriores.
            </p>
          </div>
        )}
      </div>
    </motion.div>
  )
}
