import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { AppHeader, Card, LargeButton } from '../components/UI'
import { Plus, X, Megaphone, Check, CheckCheck, AlertTriangle, Cross } from 'lucide-react'
import api from '../services/api'
import { useAuth } from '../contexts/AuthContext'

interface Lembrete {
  id: number
  titulo: string
  nota?: string | null
  data_hora_alerta: string
  minutos_antecedencia: number
  tipo: string
  remetente: string
  ativo: boolean
  lido: boolean
}

interface Props {
  onBack: () => void
}

// Partículas comuns em nomes que NÃO contam pra iniciais
const PARTICULAS = new Set(['de', 'da', 'do', 'das', 'dos', 'e', 'di', 'del', 'della'])

function iniciaisDoNome(nome: string | undefined | null): string {
  if (!nome) return '?'
  const partes = nome.trim().split(/\s+/).filter(p => p && !PARTICULAS.has(p.toLowerCase()))
  if (partes.length === 0) return '?'
  if (partes.length === 1) return partes[0][0]!.toUpperCase()
  return (partes[0][0] + partes[partes.length - 1][0]).toUpperCase()
}

export default function LembretesScreen({ onBack }: Props) {
  const { usuario } = useAuth()
  const isAdmin = !!usuario?.is_admin
  const [lembretes, setLembretes] = useState<Lembrete[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [titulo, setTitulo] = useState('')
  const [nota, setNota] = useState('')
  const [data, setData] = useState('')
  const [hora, setHora] = useState('')
  const [minutos, setMinutos] = useState(30)

  // Estado admin broadcast
  const [showAdmin, setShowAdmin] = useState(false)
  const [bcTitulo, setBcTitulo] = useState('')
  const [bcNota, setBcNota] = useState('')
  const [bcData, setBcData] = useState('')
  const [bcHora, setBcHora] = useState('')
  const [bcIgreja, setBcIgreja] = useState('')
  const [igrejasDisponiveis, setIgrejasDisponiveis] = useState<string[]>([])
  const [alcance, setAlcance] = useState<number | null>(null)
  const [bcLoading, setBcLoading] = useState(false)
  const [bcInfo, setBcInfo] = useState('')

  useEffect(() => { carregar() }, [])

  useEffect(() => {
    if (!isAdmin) return
    api.get<string[]>('/admin/igrejas').then(r => setIgrejasDisponiveis(r.data)).catch(() => {})
  }, [isAdmin])

  useEffect(() => {
    if (!isAdmin) return
    const params = bcIgreja ? `?igreja=${encodeURIComponent(bcIgreja)}` : ''
    api.get<{ total: number }>(`/admin/usuarios/contagem${params}`)
      .then(r => setAlcance(r.data.total))
      .catch(() => setAlcance(null))
  }, [isAdmin, bcIgreja])

  async function enviarBroadcast() {
    setBcInfo('')
    if (!bcTitulo || !bcData || !bcHora) { alert('Preencha título, data e hora'); return }
    setBcLoading(true)
    try {
      const r = await api.post<{ destinatarios: number }>('/admin/lembretes/broadcast', {
        titulo: bcTitulo,
        nota: bcNota || null,
        data_hora_alerta: `${bcData}T${bcHora}:00`,
        minutos_antecedencia: 30,
        igreja: bcIgreja || null,
        remetente: 'Dia de Missa',
      })
      setBcInfo(`Enviado para ${r.data.destinatarios} usuário(s).`)
      setBcTitulo(''); setBcNota(''); setBcData(''); setBcHora('')
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      alert(detail || 'Erro ao enviar broadcast')
    } finally { setBcLoading(false) }
  }

  async function carregar() {
    try {
      const r = await api.get<Lembrete[]>('/usuarios/me/lembretes')
      setLembretes(r.data)
    } catch { setLembretes([]) }
    finally { setLoading(false) }
  }

  async function criarLembreteApp(tipo: string) {
    try {
      await api.post(`/usuarios/me/lembretes/app/${tipo}`)
      carregar()
    } catch { alert('Erro ao criar lembrete') }
  }

  async function criarLembrete() {
    if (!titulo || !data || !hora) { alert('Preencha título, data e hora'); return }
    try {
      await api.post('/usuarios/me/lembretes', {
        titulo, nota: nota || null,
        data_hora_alerta: `${data}T${hora}:00`,
        minutos_antecedencia: minutos,
        tipo: 'usuario',
      })
      setShowForm(false)
      setTitulo(''); setNota(''); setData(''); setHora('')
      carregar()
    } catch { alert('Erro ao criar lembrete') }
  }

  async function deletar(id: number) {
    try { await api.delete(`/usuarios/me/lembretes/${id}`); carregar() }
    catch { alert('Erro') }
  }

  async function marcarLido(id: number) {
    try { await api.post(`/usuarios/me/lembretes/${id}/lido`); carregar() }
    catch { alert('Erro') }
  }

  async function marcarTodosLidos() {
    try { await api.post('/usuarios/me/lembretes/marcar-todos-lidos'); carregar() }
    catch { alert('Erro') }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen bg-brand-bg dark:bg-slate-900 ds-bottom-nav-padding">
      <AppHeader title="Lembretes" onBack={onBack} />

      <div className="max-w-lg mx-auto px-5 mt-6 flex flex-col gap-4">
        {/* Painel admin: broadcast com segmentação */}
        {isAdmin && (
          <Card className="p-6 border-2 border-red-500/20 bg-red-50/40 dark:bg-red-900/10">
            <button onClick={() => setShowAdmin(!showAdmin)} className="w-full flex items-center justify-between">
              <span className="flex items-center gap-2 font-bold text-red-600 dark:text-red-400">
                <Megaphone size={20} />
                Painel do administrador
              </span>
              <span className="text-xs uppercase tracking-wider text-red-600/60">
                {showAdmin ? 'Fechar' : 'Abrir'}
              </span>
            </button>

            {showAdmin && (
              <div className="mt-4 flex flex-col gap-3">
                <p className="text-xs text-red-700/70 dark:text-red-300/70">
                  Envie um lembrete em massa. Sem filtro: vai pra todos os usuários.
                </p>

                <input placeholder="Título do lembrete" value={bcTitulo} onChange={e => setBcTitulo(e.target.value)} className="w-full p-3 border border-red-200 dark:border-red-900/40 rounded-xl bg-white dark:bg-slate-900" />
                <textarea placeholder="Mensagem (opcional)" value={bcNota} onChange={e => setBcNota(e.target.value)} className="w-full p-3 border border-red-200 dark:border-red-900/40 rounded-xl bg-white dark:bg-slate-900 min-h-[80px]" />

                <div className="grid grid-cols-2 gap-3">
                  <input type="date" value={bcData} onChange={e => setBcData(e.target.value)} className="p-3 border border-red-200 dark:border-red-900/40 rounded-xl bg-white dark:bg-slate-900" />
                  <input type="time" value={bcHora} onChange={e => setBcHora(e.target.value)} className="p-3 border border-red-200 dark:border-red-900/40 rounded-xl bg-white dark:bg-slate-900" />
                </div>

                <div>
                  <label className="text-xs uppercase tracking-wider font-bold text-red-700/80 dark:text-red-300/80">Segmentar por igreja</label>
                  <select value={bcIgreja} onChange={e => setBcIgreja(e.target.value)} className="w-full p-3 border border-red-200 dark:border-red-900/40 rounded-xl bg-white dark:bg-slate-900 mt-1">
                    <option value="">Todas as igrejas</option>
                    {igrejasDisponiveis.map(ig => (
                      <option key={ig} value={ig}>{ig}</option>
                    ))}
                  </select>
                  {alcance !== null && (
                    <p className="text-xs text-red-700/60 dark:text-red-300/60 mt-1">
                      Alcance estimado: <strong>{alcance}</strong> usuário(s)
                    </p>
                  )}
                </div>

                {bcInfo && <p className="text-sm font-medium text-green-700 dark:text-green-400">{bcInfo}</p>}

                <LargeButton variant="primary" onClick={enviarBroadcast} disabled={bcLoading} icon={Megaphone} className="w-full">
                  {bcLoading ? 'Enviando...' : 'Enviar broadcast'}
                </LargeButton>
              </div>
            )}
          </Card>
        )}

        {/* Formulário de novo lembrete (modal inline) */}
        {showForm && (
          <Card className="p-6">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-bold text-lg">Novo Lembrete</h3>
              <button onClick={() => setShowForm(false)} className="p-2 bg-gray-100 dark:bg-slate-700 rounded-full">
                <X size={20} />
              </button>
            </div>
            <input placeholder="Título" value={titulo} onChange={e => setTitulo(e.target.value)} className="w-full p-3 border border-gray-200 dark:border-slate-700 rounded-xl mb-3 bg-transparent" />
            <textarea placeholder="Nota (opcional)" value={nota} onChange={e => setNota(e.target.value)} className="w-full p-3 border border-gray-200 dark:border-slate-700 rounded-xl mb-3 bg-transparent min-h-[80px]" />
            <div className="grid grid-cols-2 gap-3 mb-3">
              <input type="date" value={data} onChange={e => setData(e.target.value)} className="p-3 border border-gray-200 dark:border-slate-700 rounded-xl bg-transparent" />
              <input type="time" value={hora} onChange={e => setHora(e.target.value)} className="p-3 border border-gray-200 dark:border-slate-700 rounded-xl bg-transparent" />
            </div>
            <div className="mb-4">
              <label className="text-sm text-brand-gray-dark/60">Alerta quantos minutos antes?</label>
              <select value={minutos} onChange={e => setMinutos(Number(e.target.value))} className="w-full p-3 border border-gray-200 dark:border-slate-700 rounded-xl bg-transparent mt-1">
                <option value={0}>Na hora</option>
                <option value={15}>15 min antes</option>
                <option value={30}>30 min antes</option>
                <option value={60}>1 hora antes</option>
                <option value={120}>2 horas antes</option>
                <option value={1440}>1 dia antes</option>
              </select>
            </div>
            <LargeButton variant="primary" onClick={async () => { await criarLembrete(); }} className="w-full">Salvar Lembrete</LargeButton>
          </Card>
        )}

        {/* Cabeçalho da lista com botão "+ Lembrete" inline + marcar todos como lidos */}
        <div className="flex items-center justify-between mt-4 ml-2 mr-1">
          <h4 className="font-bold text-brand-gray-dark/40 dark:text-brand-white/40 text-xs uppercase tracking-wider">
            Seus Lembretes ({lembretes.length})
          </h4>
          <div className="flex items-center gap-2">
            {lembretes.some(l => !l.lido) && (
              <button onClick={marcarTodosLidos}
                className="flex items-center gap-1.5 text-xs font-bold text-brand-blue dark:text-brand-gold hover:opacity-70 transition-opacity">
                <CheckCheck size={14} /> Marcar todos
              </button>
            )}
            <button onClick={() => setShowForm(true)}
              className="flex items-center gap-1 px-3 py-1.5 bg-brand-blue text-white dark:bg-brand-gold dark:text-brand-blue rounded-full text-xs font-black uppercase tracking-wider active:scale-95 transition-transform">
              <Plus size={14} /> Lembrete
            </button>
          </div>
        </div>

        {lembretes.map(l => {
          // Define o ícone/conteúdo do badge por tipo:
          // - master   → ! (aviso do administrador)
          // - app / nao_acompanhada → cruz (alerta de missa do sistema)
          // - usuario  → iniciais do nome do dono (BL, AS, etc.)
          let badgeBg = 'bg-brand-blue'
          let badgeContent: any = iniciaisDoNome(usuario?.nome)
          if (l.tipo === 'master') {
            badgeBg = 'bg-red-500'
            badgeContent = <AlertTriangle size={20} />
          } else if (l.tipo === 'app' || l.tipo === 'nao_acompanhada') {
            badgeBg = 'bg-brand-gold'
            badgeContent = <Cross size={20} strokeWidth={2.5} />
          }
          return (
          <div key={l.id}
            className={`bg-brand-white dark:bg-slate-800 rounded-[20px] p-5 shadow-soft flex items-start gap-4 transition-colors ${
              l.lido ? 'border border-black/5 opacity-60' : 'border-2 border-brand-gold/50'
            }`}>
            <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold flex-shrink-0 ${badgeBg}`}>
              {badgeContent}
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <div className="font-bold">{l.titulo}</div>
                {!l.lido && <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" title="Não lido" />}
              </div>
              {l.nota && <div className="text-sm text-brand-gray-dark/60 dark:text-brand-white/60 mt-1">{l.nota}</div>}
              <div className="flex flex-wrap items-center gap-2 mt-2 text-xs text-brand-gray-dark/40 dark:text-brand-white/40">
                <span>{new Date(l.data_hora_alerta).toLocaleDateString('pt-BR', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</span>
                <span>•</span>
                <span>{l.minutos_antecedencia}min antes</span>
                {l.remetente && l.remetente !== 'Missa do Dia' && <><span>•</span><span className="text-brand-gold font-bold">{l.remetente}</span></>}
              </div>
            </div>
            <div className="flex flex-col items-end gap-2">
              {!l.lido && (
                <button onClick={() => marcarLido(l.id)} title="Marcar como lido"
                  className="p-2 text-green-600 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-full transition-colors">
                  <Check size={18} />
                </button>
              )}
              <button onClick={() => deletar(l.id)} title="Excluir"
                className="p-2 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-full transition-colors">
                <X size={18} />
              </button>
            </div>
          </div>
          )
        })}

        {!loading && lembretes.length === 0 && (
          <p className="text-center text-brand-gray-dark/40 mt-8">Nenhum lembrete ainda. Toque em <strong>+ Lembrete</strong> pra criar.</p>
        )}
      </div>
    </motion.div>
  )
}
