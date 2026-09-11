import { useState, useEffect, useRef, type FormEvent } from 'react'
import { motion } from 'motion/react'
import { login, cadastrar, recuperarSenha, redefinirSenha, loginGoogleToken } from '../services/auth'
import { Card } from '../components/UI'
import { LogIn, UserPlus, Mail, Lock, Phone, KeyRound, ArrowLeft, Church, X } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'

// Client ID do Google OAuth (Web) — definido em build via VITE_GOOGLE_CLIENT_ID.
// Enquanto ausente, o botão fica desabilitado (sem quebrar nada).
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined

interface Props {
  setScreen: (s: string) => void
  onClose?: () => void
}

type Modo = 'login' | 'cadastro' | 'esqueci' | 'redefinir'

export const AuthScreens = ({ setScreen, onClose }: Props) => {
  const { setUsuario } = useAuth()
  // Detecta se a URL tem ?token=... pra ir direto pra redefinição
  const tokenUrl = new URLSearchParams(window.location.search).get('token')
  const [modo, setModo] = useState<Modo>(tokenUrl ? 'redefinir' : 'login')
  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [celular, setCelular] = useState('')
  const [igreja, setIgreja] = useState('')
  const [senha, setSenha] = useState('')
  const [senhaConfirma, setSenhaConfirma] = useState('')
  const [token, setToken] = useState(tokenUrl || '')
  const [erro, setErro] = useState('')
  const [info, setInfo] = useState('')
  const [loading, setLoading] = useState(false)

  function concluirAutenticacao() {
    if (onClose) onClose()
    else setScreen('home')
  }

  function reset(novoModo: Modo) {
    setErro(''); setInfo(''); setSenha(''); setSenhaConfirma(''); setModo(novoModo)
  }

  // --- Login com Google (botão próprio via fluxo OAuth de token) ---
  const tokenClientRef = useRef<any>(null)
  const [googlePronto, setGooglePronto] = useState(false)

  async function handleGoogleToken(response: { access_token?: string; error?: string }) {
    if (response?.error || !response?.access_token) { setErro('Não foi possível autenticar com o Google'); return }
    setErro(''); setInfo(''); setLoading(true)
    try {
      const res = await loginGoogleToken(response.access_token)
      setUsuario(res.usuario)
      concluirAutenticacao()
    } catch {
      setErro('Falha no login com Google. Tente novamente.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return
    if (modo !== 'login' && modo !== 'cadastro') return

    const oauth2 = () => (window as any).google?.accounts?.oauth2
    function init() {
      const o = oauth2()
      if (!o) return
      tokenClientRef.current = o.initTokenClient({
        client_id: GOOGLE_CLIENT_ID,
        scope: 'email profile',
        callback: handleGoogleToken,
      })
      setGooglePronto(true)
    }

    if (oauth2()) { init(); return }
    const existente = document.getElementById('gsi-script') as HTMLScriptElement | null
    if (existente) { existente.addEventListener('load', init); return () => existente.removeEventListener('load', init) }
    const s = document.createElement('script')
    s.src = 'https://accounts.google.com/gsi/client'
    s.async = true; s.defer = true; s.id = 'gsi-script'
    s.onload = init
    document.body.appendChild(s)
  }, [modo])

  function entrarComGoogle() {
    if (!tokenClientRef.current) { setErro('Google ainda carregando — tente de novo em instantes'); return }
    setErro(''); setInfo('')
    tokenClientRef.current.requestAccessToken()
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setErro(''); setInfo('')

    if (modo === 'login') {
      if (!email || !senha) { setErro('Preencha todos os campos'); return }
      setLoading(true)
      try {
        const res = await login(email, senha)
        setUsuario(res.usuario)
        concluirAutenticacao()
      } catch { setErro('Email ou senha inválidos') }
      finally { setLoading(false) }
      return
    }

    if (modo === 'cadastro') {
      if (!nome || !email || !celular || !senha || !senhaConfirma) {
        setErro('Preencha todos os campos'); return
      }
      if (senha !== senhaConfirma) { setErro('As senhas não coincidem'); return }
      if (senha.length < 4) { setErro('A senha precisa ter pelo menos 4 caracteres'); return }
      setLoading(true)
      try {
        await cadastrar(nome, email, senha, celular, igreja || undefined)
        const res = await login(email, senha)
        setUsuario(res.usuario)
        concluirAutenticacao()
      } catch { setErro('Não foi possível criar a conta (e-mail pode já estar em uso)') }
      finally { setLoading(false) }
      return
    }

    if (modo === 'esqueci') {
      if (!email) { setErro('Informe seu e-mail'); return }
      setLoading(true)
      try {
        await recuperarSenha(email)
        setInfo('Se o e-mail estiver cadastrado, enviaremos um link em até alguns minutos. Verifique sua caixa de entrada e spam.')
      } catch { setErro('Não foi possível processar agora — tente em alguns minutos') }
      finally { setLoading(false) }
      return
    }

    if (modo === 'redefinir') {
      if (!token || !senha || !senhaConfirma) { setErro('Preencha todos os campos'); return }
      if (senha !== senhaConfirma) { setErro('As senhas não coincidem'); return }
      if (senha.length < 4) { setErro('A senha precisa ter pelo menos 4 caracteres'); return }
      setLoading(true)
      try {
        await redefinirSenha(token, senha)
        setInfo('Senha redefinida com sucesso. Faça login com sua nova senha.')
        // Limpa token da URL e troca pra login
        window.history.replaceState({}, '', window.location.pathname)
        setTimeout(() => reset('login'), 1500)
      } catch { setErro('Token inválido ou expirado. Solicite um novo link.') }
      finally { setLoading(false) }
      return
    }
  }

  const titulo = {
    login: 'Entrar',
    cadastro: 'Criar conta',
    esqueci: 'Recuperar senha',
    redefinir: 'Redefinir senha',
  }[modo]

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className={onClose
        ? 'fixed inset-0 z-[80] flex items-start justify-center overflow-y-auto bg-brand-blue/45 px-3 py-4 sm:p-6 backdrop-blur-[2px]'
        : 'min-h-screen flex items-center justify-center p-6'}
      role={onClose ? 'dialog' : undefined}
      aria-modal={onClose || undefined}
      aria-labelledby={onClose ? 'acesso-titulo' : undefined}
      onClick={onClose}
    >
      <div className="relative w-full max-w-md pb-4" onClick={event => event.stopPropagation()}>
        {onClose && (
          <button
            type="button"
            onClick={onClose}
            aria-label="Fechar e continuar sem conta"
            className="absolute right-1 top-1 z-10 rounded-full bg-brand-white/90 p-2 text-brand-blue shadow-soft hover:bg-brand-white dark:bg-slate-800 dark:text-brand-gold"
          >
            <X size={20} />
          </button>
        )}
        <div className={`text-center ${onClose ? 'mb-3 pt-1' : 'mb-10'}`}>
          <h1 id={onClose ? 'acesso-titulo' : undefined} className={`${onClose ? 'text-4xl' : 'text-5xl'} font-serif font-black text-brand-blue dark:text-brand-gold mb-2`}>Dia de Missa</h1>
          <p className="text-brand-gold font-bold italic text-lg">Liturgia Diária</p>
        </div>

        <Card className={`${onClose ? 'p-4 sm:p-6' : 'p-8'} shadow-strong`}>
          {(modo === 'esqueci' || modo === 'redefinir') && (
            <button
              type="button"
              onClick={() => reset('login')}
              className="flex items-center gap-2 text-sm text-brand-blue/60 dark:text-brand-gold/60 mb-4 hover:opacity-100 transition-opacity"
            >
              <ArrowLeft size={16} /> Voltar pro login
            </button>
          )}

          <h2 className="text-2xl font-serif font-black text-brand-blue dark:text-brand-gold mb-4">{titulo}</h2>

          <form onSubmit={handleSubmit}>
            {erro && <p className="text-red-500 text-sm font-bold mb-4 text-center">{erro}</p>}
            {info && <p className="text-green-600 text-sm font-medium mb-4 text-center">{info}</p>}

            {modo === 'cadastro' && (
              <div className="mb-3">
                <label className="text-xs font-bold uppercase tracking-widest text-brand-gray-dark/60 mb-1 block">Nome</label>
                <div className="flex items-center gap-3 bg-gray-50 dark:bg-slate-800 rounded-2xl px-4 py-3 border border-gray-200 dark:border-slate-700">
                  <UserPlus size={20} className="text-brand-gold" />
                  <input className="bg-transparent w-full text-lg font-medium outline-none placeholder:text-gray-400 dark:text-white" placeholder="Seu nome" value={nome} onChange={e => setNome(e.target.value)} />
                </div>
              </div>
            )}

            {(modo === 'login' || modo === 'cadastro' || modo === 'esqueci') && (
              <div className="mb-3">
                <label className="text-xs font-bold uppercase tracking-widest text-brand-gray-dark/60 mb-1 block">E-mail</label>
                <div className="flex items-center gap-3 bg-gray-50 dark:bg-slate-800 rounded-2xl px-4 py-3 border border-gray-200 dark:border-slate-700">
                  <Mail size={20} className="text-brand-gold" />
                  <input type="email" className="bg-transparent w-full text-lg font-medium outline-none placeholder:text-gray-400 dark:text-white" placeholder="seu@email.com" value={email} onChange={e => setEmail(e.target.value)} />
                </div>
              </div>
            )}

            {modo === 'cadastro' && (
              <div className="mb-3">
                <label className="text-xs font-bold uppercase tracking-widest text-brand-gray-dark/60 mb-1 block">Celular (WhatsApp)</label>
                <div className="flex items-center gap-3 bg-gray-50 dark:bg-slate-800 rounded-2xl px-4 py-3 border border-gray-200 dark:border-slate-700">
                  <Phone size={20} className="text-brand-gold" />
                  <input type="tel" className="bg-transparent w-full text-lg font-medium outline-none placeholder:text-gray-400 dark:text-white" placeholder="(21) 99999-9999" value={celular} onChange={e => setCelular(e.target.value)} />
                </div>
              </div>
            )}

            {modo === 'cadastro' && (
              <div className="mb-3">
                <label className="text-xs font-bold uppercase tracking-widest text-brand-gray-dark/60 mb-1 block">Igreja que frequenta (opcional)</label>
                <div className="flex items-center gap-3 bg-gray-50 dark:bg-slate-800 rounded-2xl px-4 py-3 border border-gray-200 dark:border-slate-700">
                  <Church size={20} className="text-brand-gold" />
                  <input className="bg-transparent w-full text-lg font-medium outline-none placeholder:text-gray-400 dark:text-white" placeholder="Ex.: Capela PUC-Rio" value={igreja} onChange={e => setIgreja(e.target.value)} />
                </div>
              </div>
            )}

            {modo === 'redefinir' && (
              <div className="mb-3">
                <label className="text-xs font-bold uppercase tracking-widest text-brand-gray-dark/60 mb-1 block">Token</label>
                <div className="flex items-center gap-3 bg-gray-50 dark:bg-slate-800 rounded-2xl px-4 py-3 border border-gray-200 dark:border-slate-700">
                  <KeyRound size={20} className="text-brand-gold" />
                  <input className="bg-transparent w-full text-sm font-medium outline-none placeholder:text-gray-400 dark:text-white" placeholder="Token do e-mail" value={token} onChange={e => setToken(e.target.value)} />
                </div>
              </div>
            )}

            {(modo === 'login' || modo === 'cadastro' || modo === 'redefinir') && (
              <div className="mb-3">
                <label className="text-xs font-bold uppercase tracking-widest text-brand-gray-dark/60 mb-1 block">
                  {modo === 'redefinir' ? 'Nova senha' : 'Senha'}
                </label>
                <div className="flex items-center gap-3 bg-gray-50 dark:bg-slate-800 rounded-2xl px-4 py-3 border border-gray-200 dark:border-slate-700">
                  <Lock size={20} className="text-brand-gold" />
                  <input type="password" className="bg-transparent w-full text-lg font-medium outline-none placeholder:text-gray-400 dark:text-white" placeholder="••••••" value={senha} onChange={e => setSenha(e.target.value)} />
                </div>
              </div>
            )}

            {(modo === 'cadastro' || modo === 'redefinir') && (
              <div className="mb-4">
                <label className="text-xs font-bold uppercase tracking-widest text-brand-gray-dark/60 mb-1 block">Confirme a senha</label>
                <div className="flex items-center gap-3 bg-gray-50 dark:bg-slate-800 rounded-2xl px-4 py-3 border border-gray-200 dark:border-slate-700">
                  <Lock size={20} className="text-brand-gold" />
                  <input type="password" className="bg-transparent w-full text-lg font-medium outline-none placeholder:text-gray-400 dark:text-white" placeholder="••••••" value={senhaConfirma} onChange={e => setSenhaConfirma(e.target.value)} />
                </div>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-2 rounded-full bg-brand-blue text-white font-extrabold text-[15px] py-2.5 min-h-[46px] shadow-soft active:scale-[0.98] transition-transform disabled:opacity-60 disabled:cursor-not-allowed mb-3"
            >
              {!loading && <LogIn size={20} />}
              {loading
                ? 'Aguarde...'
                : modo === 'login'
                  ? 'Entrar'
                  : modo === 'cadastro'
                    ? 'Criar conta'
                    : modo === 'esqueci'
                      ? 'Enviar link de recuperação'
                      : 'Redefinir senha'}
            </button>
          </form>

          {modo === 'login' && (
            <>
              <button
                type="button"
                onClick={() => reset('esqueci')}
                className="w-full text-center text-sm font-medium text-brand-blue dark:text-brand-gold hover:opacity-70 transition-opacity mb-3"
              >
                Esqueci minha senha
              </button>
              <p className="text-center text-sm text-brand-gray-dark dark:text-brand-white/70">
                Não tem conta?{' '}
                <button
                  type="button"
                  onClick={() => reset('cadastro')}
                  className="font-bold text-brand-blue dark:text-brand-gold hover:opacity-70 transition-opacity"
                >
                  Cadastre-se
                </button>
              </p>
            </>
          )}

          {modo === 'cadastro' && (
            <p className="text-center text-sm text-brand-gray-dark dark:text-brand-white/70">
              Já tem conta?{' '}
              <button
                type="button"
                onClick={() => reset('login')}
                className="font-bold text-brand-blue dark:text-brand-gold hover:opacity-70 transition-opacity"
              >
                Faça login
              </button>
            </p>
          )}

          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="mt-5 w-full text-center text-sm font-medium text-brand-gray-dark/65 hover:text-brand-blue dark:text-brand-white/65 dark:hover:text-brand-gold"
            >
              Continuar sem conta
            </button>
          )}
        </Card>

        {(modo === 'login' || modo === 'cadastro') && (
          <div className="mt-6 flex flex-col gap-3">
            <div className="flex items-center gap-3">
              <div className="flex-1 h-px bg-brand-gray/40" />
              <span className="text-xs font-bold text-brand-gray-dark/40 uppercase tracking-wider">ou</span>
              <div className="flex-1 h-px bg-brand-gray/40" />
            </div>
            {GOOGLE_CLIENT_ID ? (
              <button
                type="button"
                onClick={entrarComGoogle}
                disabled={loading || !googlePronto}
                className="w-full flex items-center justify-center gap-3 rounded-full bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 text-brand-gray-dark dark:text-white font-bold text-[15px] py-2.5 min-h-[46px] shadow-soft active:scale-[0.98] transition-transform disabled:opacity-60 disabled:cursor-not-allowed"
              >
                <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
                {modo === 'cadastro' ? 'Cadastrar com o Google' : 'Continuar com o Google'}
              </button>
            ) : (
              <button disabled
                className="flex items-center justify-center gap-3 w-full bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-full px-6 py-2.5 font-bold text-[15px] opacity-60 cursor-not-allowed shadow-soft min-h-[46px]">
                <svg width="18" height="18" viewBox="0 0 24 24"><path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
                <span className="text-brand-text dark:text-white">Google (configurando…)</span>
              </button>
            )}
          </div>
        )}

        <p className="text-center text-xs text-brand-gray-dark/30 mt-8">Dia de Missa © 2026</p>
      </div>
    </motion.div>
  )
}
