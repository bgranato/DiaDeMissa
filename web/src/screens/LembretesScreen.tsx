import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { AppHeader, Card, LargeButton } from '../components/UI'
import { Bell, Plus, X, Church, CalendarClock } from 'lucide-react'
import api from '../services/api'

interface Lembrete {
  id: number
  titulo: string
  nota?: string | null
  data_hora_alerta: string
  minutos_antecedencia: number
  tipo: string
  remetente: string
  ativo: boolean
}

interface Props {
  onBack: () => void
}

export default function LembretesScreen({ onBack }: Props) {
  const [lembretes, setLembretes] = useState<Lembrete[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [titulo, setTitulo] = useState('')
  const [nota, setNota] = useState('')
  const [data, setData] = useState('')
  const [hora, setHora] = useState('')
  const [minutos, setMinutos] = useState(30)

  useEffect(() => { carregar() }, [])

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

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen bg-brand-bg dark:bg-slate-900 pb-32">
      <AppHeader title="Lembretes" showAccessibility={false} onBack={onBack} />

      <div className="max-w-lg mx-auto px-5 mt-6 flex flex-col gap-4">
        {/* Lembretes pré-definidos */}
        <Card className="p-6">
          <h3 className="font-bold text-lg mb-4 flex items-center gap-2">
            <Church size={20} className="text-brand-gold" />
            Lembretes da Igreja
          </h3>
          <button onClick={() => criarLembreteApp('domingo')}
            className="w-full flex items-center gap-4 p-4 bg-brand-blue/[0.08] dark:bg-slate-800 rounded-2xl active:scale-[0.98] transition-transform mb-3">
            <CalendarClock size={24} className="text-brand-gold" />
            <div className="text-left flex-1">
              <p className="font-bold">Missa de Domingo</p>
              <p className="text-sm text-brand-gray-dark/60">Alerta 30min antes, às 11h</p>
            </div>
            <Plus size={20} />
          </button>
        </Card>

        {/* Formulário de novo lembrete */}
        {showForm ? (
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
            <LargeButton variant="primary" onClick={criarLembrete} className="w-full">Salvar Lembrete</LargeButton>
          </Card>
        ) : (
          <button onClick={() => setShowForm(true)}
            className="flex items-center justify-center gap-3 w-full p-5 bg-brand-white dark:bg-slate-800 rounded-[24px] shadow-soft border border-black/5 active:scale-[0.98] transition-transform font-bold text-brand-blue dark:text-brand-gold">
            <Plus size={24} /> Novo Lembrete Personalizado
          </button>
        )}

        {/* Lista de lembretes */}
        <h4 className="font-bold text-brand-gray-dark/40 text-xs uppercase tracking-wider mt-4 ml-2">
          Seus Lembretes ({lembretes.length})
        </h4>

        {lembretes.map(l => (
          <div key={l.id} className="bg-brand-white dark:bg-slate-800 rounded-[20px] p-5 shadow-soft border border-black/5 flex items-start gap-4">
            <div className={`w-10 h-10 rounded-full flex items-center justify-center text-white text-sm font-bold ${l.tipo === 'master' ? 'bg-red-500' : l.tipo === 'app' ? 'bg-brand-gold' : 'bg-brand-blue'}`}>
              {l.tipo === 'master' ? 'ADM' : l.tipo === 'app' ? 'AP' : 'U'}
            </div>
            <div className="flex-1">
              <div className="font-bold">{l.titulo}</div>
              {l.nota && <div className="text-sm text-brand-gray-dark/60 mt-1">{l.nota}</div>}
              <div className="flex items-center gap-2 mt-2 text-xs text-brand-gray-dark/40">
                <span>{new Date(l.data_hora_alerta).toLocaleDateString('pt-BR', { weekday: 'short', day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' })}</span>
                <span>•</span>
                <span>{l.minutos_antecedencia}min antes</span>
                {l.remetente !== 'usuario' && <><span>•</span><span className="text-brand-gold font-bold">{l.remetente}</span></>}
              </div>
            </div>
            <button onClick={() => deletar(l.id)} className="p-2 text-red-500 hover:opacity-80">
              <X size={18} />
            </button>
          </div>
        ))}

        {!loading && lembretes.length === 0 && (
          <p className="text-center text-brand-gray-dark/40 mt-8">Nenhum lembrete ainda.</p>
        )}
      </div>
    </motion.div>
  )
}
