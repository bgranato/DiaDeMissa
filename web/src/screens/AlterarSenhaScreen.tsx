import { useState, type FormEvent } from 'react'
import { motion } from 'motion/react'
import { AppHeader, Card, LargeButton } from '../components/UI'
import { Lock, Save } from 'lucide-react'
import { alterarSenha, recuperarSenha } from '../services/auth'
import { useAuth } from '../contexts/AuthContext'

interface Props {
  onBack: () => void
}

export const AlterarSenhaScreen = ({ onBack }: Props) => {
  const { usuario } = useAuth()
  const [senhaAtual, setSenhaAtual] = useState('')
  const [novaSenha, setNovaSenha] = useState('')
  const [confirma, setConfirma] = useState('')
  const [erro, setErro] = useState('')
  const [info, setInfo] = useState('')
  const [loading, setLoading] = useState(false)
  const [enviandoReset, setEnviandoReset] = useState(false)

  async function pedirLinkRecuperacao() {
    if (!usuario?.email) { setErro('Sessão sem e-mail; faça login novamente'); return }
    setErro(''); setInfo(''); setEnviandoReset(true)
    try {
      await recuperarSenha(usuario.email)
      setInfo(`Enviamos um link de recuperação para ${usuario.email}. Verifique sua caixa de entrada.`)
    } catch {
      setErro('Não foi possível enviar agora. Tente novamente em alguns minutos.')
    } finally {
      setEnviandoReset(false)
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setErro(''); setInfo('')
    if (!senhaAtual || !novaSenha || !confirma) { setErro('Preencha todos os campos'); return }
    if (novaSenha !== confirma) { setErro('As senhas não coincidem'); return }
    if (novaSenha.length < 4) { setErro('A nova senha precisa ter pelo menos 4 caracteres'); return }
    setLoading(true)
    try {
      await alterarSenha(senhaAtual, novaSenha)
      setInfo('Senha alterada com sucesso')
      setSenhaAtual(''); setNovaSenha(''); setConfirma('')
    } catch (e: any) {
      const detail = e?.response?.data?.detail
      setErro(detail || 'Não foi possível alterar a senha')
    } finally { setLoading(false) }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen bg-brand-bg dark:bg-slate-900 ds-bottom-nav-padding">
      <AppHeader title="Alterar senha" onBack={onBack} />

      <div className="max-w-lg mx-auto px-5 mt-6">
        <Card className="p-6">
          <form onSubmit={handleSubmit} className="flex flex-col gap-4">
            {erro && <p className="text-red-500 text-sm font-bold text-center">{erro}</p>}
            {info && <p className="text-green-600 text-sm font-medium text-center">{info}</p>}

            <div>
              <label className="text-xs font-bold uppercase tracking-widest text-brand-gray-dark/60 dark:text-brand-white/60 mb-2 block">Senha atual</label>
              <div className="flex items-center gap-3 bg-gray-50 dark:bg-slate-800 rounded-2xl px-5 py-4 border border-gray-200 dark:border-slate-700">
                <Lock size={20} className="text-brand-gold" />
                <input type="password" className="bg-transparent w-full text-lg font-medium outline-none placeholder:text-gray-400 dark:text-white" placeholder="••••••" value={senhaAtual} onChange={e => setSenhaAtual(e.target.value)} />
              </div>
              <button
                type="button"
                onClick={pedirLinkRecuperacao}
                disabled={enviandoReset}
                className="text-sm font-medium text-brand-blue dark:text-brand-gold hover:opacity-70 transition-opacity mt-2 disabled:opacity-40"
              >
                {enviandoReset ? 'Enviando...' : 'Esqueci minha senha'}
              </button>
            </div>

            <div>
              <label className="text-xs font-bold uppercase tracking-widest text-brand-gray-dark/60 dark:text-brand-white/60 mb-2 block">Nova senha</label>
              <div className="flex items-center gap-3 bg-gray-50 dark:bg-slate-800 rounded-2xl px-5 py-4 border border-gray-200 dark:border-slate-700">
                <Lock size={20} className="text-brand-gold" />
                <input type="password" className="bg-transparent w-full text-lg font-medium outline-none placeholder:text-gray-400 dark:text-white" placeholder="••••••" value={novaSenha} onChange={e => setNovaSenha(e.target.value)} />
              </div>
            </div>

            <div>
              <label className="text-xs font-bold uppercase tracking-widest text-brand-gray-dark/60 dark:text-brand-white/60 mb-2 block">Confirme a nova senha</label>
              <div className="flex items-center gap-3 bg-gray-50 dark:bg-slate-800 rounded-2xl px-5 py-4 border border-gray-200 dark:border-slate-700">
                <Lock size={20} className="text-brand-gold" />
                <input type="password" className="bg-transparent w-full text-lg font-medium outline-none placeholder:text-gray-400 dark:text-white" placeholder="••••••" value={confirma} onChange={e => setConfirma(e.target.value)} />
              </div>
            </div>

            <LargeButton variant="primary" onClick={() => handleSubmit({ preventDefault: () => {} } as FormEvent)} disabled={loading} icon={Save} className="w-full mt-2">
              {loading ? 'Alterando...' : 'Alterar senha'}
            </LargeButton>
          </form>

          <button
            type="button"
            onClick={pedirLinkRecuperacao}
            disabled={enviandoReset}
            className="w-full text-center text-sm font-medium text-brand-blue dark:text-brand-gold hover:opacity-70 transition-opacity mt-4 disabled:opacity-40"
          >
            {enviandoReset ? 'Enviando...' : 'Esqueci minha senha atual'}
          </button>
        </Card>
      </div>
    </motion.div>
  )
}
