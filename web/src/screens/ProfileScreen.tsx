import { useState, useEffect } from 'react'
import { motion } from 'motion/react'
import { AppHeader, Card } from '../components/UI'
import { User, Bell, LogOut, KeyRound, Mail } from 'lucide-react'
import type { Usuario } from '../types/usuario'
import { getPreferencias, atualizarPreferencias } from '../services/preferencias'

interface Props {
  setScreen: (s: string) => void
  usuario: Usuario | null
  onLogout: () => void
}

export const ProfileScreen = ({ setScreen, usuario, onLogout }: Props) => {
  const [alertaEmail, setAlertaEmail] = useState<boolean | null>(null)

  useEffect(() => {
    getPreferencias()
      .then(p => setAlertaEmail(p.alerta_missa_email))
      .catch(() => setAlertaEmail(true))
  }, [])

  async function toggleAlertaEmail() {
    if (alertaEmail === null) return
    const novo = !alertaEmail
    setAlertaEmail(novo) // otimista
    try {
      await atualizarPreferencias({ alerta_missa_email: novo })
    } catch {
      setAlertaEmail(!novo) // reverte em erro
    }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen bg-brand-bg dark:bg-slate-900 ds-bottom-nav-padding">
      <AppHeader title="Perfil" onBack={() => setScreen('home')} />

      <div className="max-w-lg mx-auto px-5 mt-6 flex flex-col gap-4">
        <Card className="flex items-center gap-6 p-6">
          <div className="w-20 h-20 rounded-full bg-brand-blue flex items-center justify-center text-white text-3xl font-black">
            {usuario?.nome?.charAt(0).toUpperCase() || '?'}
          </div>
          <div>
            <h2 className="text-2xl font-bold">{usuario?.nome || 'Usuário'}</h2>
            <p className="text-sm text-brand-gray-dark/60">{usuario?.email}</p>
          </div>
        </Card>

        <div className="flex flex-col gap-3 mt-4">
          <button onClick={() => setScreen('meus-dados')} className="flex items-center gap-4 bg-white dark:bg-slate-800 p-5 rounded-2xl shadow-soft border border-black/5 active:scale-[0.98] transition-transform">
            <User size={24} className="text-brand-blue" />
            <span className="font-bold flex-1 text-left">Meus dados</span>
            <span className="text-brand-gray-dark/40">→</span>
          </button>
          <button onClick={() => setScreen('alterar-senha')} className="flex items-center gap-4 bg-white dark:bg-slate-800 p-5 rounded-2xl shadow-soft border border-black/5 active:scale-[0.98] transition-transform">
            <KeyRound size={24} className="text-brand-gold" />
            <span className="font-bold flex-1 text-left">Alterar senha</span>
            <span className="text-brand-gray-dark/40">→</span>
          </button>
          <button onClick={() => setScreen('reminders')} className="flex items-center gap-4 bg-white dark:bg-slate-800 p-5 rounded-2xl shadow-soft border border-black/5 active:scale-[0.98] transition-transform">
            <Bell size={24} className="text-brand-gold" />
            <span className="font-bold flex-1 text-left">Lembretes</span>
            <span className="text-brand-gray-dark/40">→</span>
          </button>

          {/* Alerta por e-mail quando a missa entra no sistema (ligado por padrão) */}
          <div className="flex items-center gap-4 bg-white dark:bg-slate-800 p-5 rounded-2xl shadow-soft border border-black/5">
            <Mail size={24} className="text-brand-blue" />
            <div className="flex-1 text-left min-w-0">
              <span className="font-bold block">Avisar por e-mail</span>
              <span className="text-xs text-brand-gray-dark/60">Quando a missa do dia entra no sistema</span>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={!!alertaEmail}
              aria-label="Avisar por e-mail quando a missa entra no sistema"
              onClick={toggleAlertaEmail}
              disabled={alertaEmail === null}
              className={`relative w-12 h-7 rounded-full transition-colors flex-shrink-0 disabled:opacity-40 ${alertaEmail ? 'bg-brand-gold' : 'bg-gray-300 dark:bg-slate-600'}`}
            >
              <span className={`absolute top-1 left-1 w-5 h-5 rounded-full bg-white shadow transition-transform ${alertaEmail ? 'translate-x-5' : ''}`} />
            </button>
          </div>

          <hr className="my-2 border-gray-200 dark:border-slate-700" />

          <button onClick={onLogout} className="flex items-center gap-4 bg-white dark:bg-slate-800 p-5 rounded-2xl shadow-soft border border-red-100 active:scale-[0.98] transition-transform">
            <LogOut size={24} className="text-red-500" />
            <span className="font-bold flex-1 text-left text-red-500">Sair da conta</span>
          </button>
        </div>

        <div className="mt-8 text-center">
          <p className="text-xs text-brand-gray-dark/30">Dia de Missa v1.0.0</p>
          <p className="text-[10px] text-brand-gray-dark/20 mt-1">Fonte: Arquidiocese do Rio de Janeiro</p>
        </div>
      </div>
    </motion.div>
  )
}
