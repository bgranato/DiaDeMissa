import { useState, type FormEvent } from 'react'
import { motion } from 'motion/react'
import { AppHeader, Card, LargeButton } from '../components/UI'
import { User, Mail, Phone, Save, Church } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { atualizarUsuario } from '../services/auth'

interface Props {
  onBack: () => void
}

export const MeusDadosScreen = ({ onBack }: Props) => {
  const { usuario, setUsuario } = useAuth()
  const [nome, setNome] = useState(usuario?.nome || '')
  const [email, setEmail] = useState(usuario?.email || '')
  const [celular, setCelular] = useState(usuario?.celular || '')
  const [igreja, setIgreja] = useState(usuario?.igreja || '')
  const [erro, setErro] = useState('')
  const [info, setInfo] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setErro(''); setInfo('')
    if (!nome || !email) { setErro('Nome e e-mail são obrigatórios'); return }
    setLoading(true)
    try {
      const atualizado = await atualizarUsuario({
        nome,
        email,
        celular: celular || null,
        igreja: igreja || null,
      } as any)
      setUsuario(atualizado)
      setInfo('Dados atualizados')
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      setErro(detail || 'Não foi possível atualizar')
    } finally { setLoading(false) }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen bg-brand-bg dark:bg-slate-900 ds-bottom-nav-padding">
      <AppHeader title="Meus dados" onBack={onBack} />

      <div className="max-w-lg mx-auto px-5 mt-6">
        <Card className="p-6">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {erro && <p className="text-red-500 text-sm font-bold text-center">{erro}</p>}
            {info && <p className="text-green-600 text-sm font-medium text-center">{info}</p>}

            <div>
              <label className="text-xs font-bold uppercase tracking-widest text-brand-gray-dark/60 dark:text-brand-white/60 mb-2 block">Nome</label>
              <div className="flex items-center gap-3 bg-gray-50 dark:bg-slate-800 rounded-2xl px-5 py-4 border border-gray-200 dark:border-slate-700">
                <User size={20} className="text-brand-gold" />
                <input className="bg-transparent w-full text-lg font-medium outline-none placeholder:text-gray-400 dark:text-white" placeholder="Seu nome" value={nome} onChange={e => setNome(e.target.value)} />
              </div>
            </div>

            <div>
              <label className="text-xs font-bold uppercase tracking-widest text-brand-gray-dark/60 dark:text-brand-white/60 mb-2 block">E-mail</label>
              <div className="flex items-center gap-3 bg-gray-50 dark:bg-slate-800 rounded-2xl px-5 py-4 border border-gray-200 dark:border-slate-700">
                <Mail size={20} className="text-brand-gold" />
                <input type="email" className="bg-transparent w-full text-lg font-medium outline-none placeholder:text-gray-400 dark:text-white" placeholder="seu@email.com" value={email} onChange={e => setEmail(e.target.value)} />
              </div>
            </div>

            <div>
              <label className="text-xs font-bold uppercase tracking-widest text-brand-gray-dark/60 dark:text-brand-white/60 mb-2 block">Celular (WhatsApp)</label>
              <div className="flex items-center gap-3 bg-gray-50 dark:bg-slate-800 rounded-2xl px-5 py-4 border border-gray-200 dark:border-slate-700">
                <Phone size={20} className="text-brand-gold" />
                <input type="tel" className="bg-transparent w-full text-lg font-medium outline-none placeholder:text-gray-400 dark:text-white" placeholder="(21) 99999-9999" value={celular} onChange={e => setCelular(e.target.value)} />
              </div>
            </div>

            <div>
              <label className="text-xs font-bold uppercase tracking-widest text-brand-gray-dark/60 dark:text-brand-white/60 mb-2 block">Igreja que frequenta</label>
              <div className="flex items-center gap-3 bg-gray-50 dark:bg-slate-800 rounded-2xl px-5 py-4 border border-gray-200 dark:border-slate-700">
                <Church size={20} className="text-brand-gold" />
                <input className="bg-transparent w-full text-lg font-medium outline-none placeholder:text-gray-400 dark:text-white" placeholder="Ex.: Capela PUC-Rio" value={igreja} onChange={e => setIgreja(e.target.value)} />
              </div>
            </div>

            <LargeButton variant="primary" onClick={() => handleSubmit({ preventDefault: () => {} } as FormEvent)} disabled={loading} icon={Save} className="w-full mt-2">
              {loading ? 'Salvando...' : 'Salvar alterações'}
            </LargeButton>
          </form>
        </Card>
      </div>
    </motion.div>
  )
}
