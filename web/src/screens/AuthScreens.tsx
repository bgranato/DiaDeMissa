import { useState } from 'react'
import { motion } from 'motion/react'
import { login, cadastrar } from '../services/auth'
import { LargeButton, Card } from '../components/UI'
import { LogIn, UserPlus, Mail, Lock } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

interface Props {
  setScreen: (s: string) => void
}

export const AuthScreens = ({ setScreen }: Props) => {
  const { setUsuario } = useAuth()
  const [modo, setModo] = useState<'login' | 'cadastro'>('login')
  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!email || !senha || (modo === 'cadastro' && !nome)) { setErro('Preencha todos os campos'); return }
    setLoading(true); setErro('')
    try {
      if (modo === 'login') {
        const res = await login(email, senha)
        setUsuario(res.usuario)
      } else {
        await cadastrar(nome, email, senha)
        const res = await login(email, senha)
        setUsuario(res.usuario)
      }
      setScreen('home')
    } catch { setErro(modo === 'login' ? 'Email ou senha inválidos' : 'Não foi possível criar a conta') }
    finally { setLoading(false) }
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="min-h-screen flex items-center justify-center p-6">
      <div className="w-full max-w-md">
        <div className="text-center mb-10">
          <h1 className="text-5xl font-serif font-black text-brand-blue dark:text-brand-gold mb-2">Dia de Missa</h1>
          <p className="text-brand-gold font-bold italic text-lg">Liturgia Diária</p>
        </div>

        <Card className="p-8 shadow-strong">
          <form onSubmit={handleSubmit}>
            {erro && <p className="text-red-500 text-sm font-bold mb-4 text-center">{erro}</p>}

            {modo === 'cadastro' && (
              <div className="mb-4">
                <label className="text-xs font-bold uppercase tracking-widest text-brand-gray-dark/60 mb-2 block">Nome</label>
                <div className="flex items-center gap-3 bg-gray-50 dark:bg-slate-800 rounded-2xl px-5 py-4 border border-gray-200 dark:border-slate-700">
                  <UserPlus size={20} className="text-brand-gold" />
                  <input className="bg-transparent w-full text-lg font-medium outline-none placeholder:text-gray-400 dark:text-white" placeholder="Seu nome" value={nome} onChange={e => setNome(e.target.value)} />
                </div>
              </div>
            )}

            <div className="mb-4">
              <label className="text-xs font-bold uppercase tracking-widest text-brand-gray-dark/60 mb-2 block">Email</label>
              <div className="flex items-center gap-3 bg-gray-50 dark:bg-slate-800 rounded-2xl px-5 py-4 border border-gray-200 dark:border-slate-700">
                <Mail size={20} className="text-brand-gold" />
                <input type="email" className="bg-transparent w-full text-lg font-medium outline-none placeholder:text-gray-400 dark:text-white" placeholder="seu@email.com" value={email} onChange={e => setEmail(e.target.value)} />
              </div>
            </div>

            <div className="mb-6">
              <label className="text-xs font-bold uppercase tracking-widest text-brand-gray-dark/60 mb-2 block">Senha</label>
              <div className="flex items-center gap-3 bg-gray-50 dark:bg-slate-800 rounded-2xl px-5 py-4 border border-gray-200 dark:border-slate-700">
                <Lock size={20} className="text-brand-gold" />
                <input type="password" className="bg-transparent w-full text-lg font-medium outline-none placeholder:text-gray-400 dark:text-white" placeholder="••••••" value={senha} onChange={e => setSenha(e.target.value)} />
              </div>
            </div>

            <LargeButton variant="primary" onClick={handleSubmit} disabled={loading} icon={LogIn} className="w-full mb-3">
              {loading ? 'Aguarde...' : modo === 'login' ? 'Entrar' : 'Criar conta'}
            </LargeButton>
          </form>

          <button onClick={() => { setModo(modo === 'login' ? 'cadastro' : 'login'); setErro('') }} className="w-full text-center text-sm font-bold text-brand-blue/60 dark:text-brand-gold/60 hover:opacity-100 transition-opacity">
            {modo === 'login' ? 'Não tem conta? Cadastre-se' : 'Já tem conta? Faça login'}
          </button>
        </Card>

        <div className="mt-6 flex flex-col gap-3">
          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-brand-gray/40" />
            <span className="text-xs font-bold text-brand-gray-dark/40 uppercase tracking-wider">ou</span>
            <div className="flex-1 h-px bg-brand-gray/40" />
          </div>
          <button onClick={() => alert('Login com Google em breve')}
            className="flex items-center justify-center gap-3 w-full bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-[24px] px-8 py-5 font-bold text-lg transition-all active:scale-95 shadow-soft min-h-[68px]">
            <svg width="24" height="24" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
            <span className="text-brand-text dark:text-white">Continuar com Google</span>
          </button>
        </div>

        <p className="text-center text-xs text-brand-gray-dark/30 mt-8">Dia de Missa © 2026</p>
      </div>
    </motion.div>
  )
}
