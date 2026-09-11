import { useState, useEffect, useCallback, useRef } from 'react'
import { AnimatePresence } from 'motion/react'
import { useAuth } from './contexts/AuthContext'
import { getMissaHoje, getMissaPorData, getProximaMissa } from './services/missa'
import api from './services/api'
import { pausarConviteApoioAposPagamento } from './services/apoioExibicao'
import { logNav, logError } from './services/logger'
import { HomeScreen } from './screens/HomeScreen'
import { ReadingScreen } from './screens/ReadingScreen'
import { CalendarScreen } from './screens/CalendarScreen'
import { JornadaScreen } from './screens/JornadaScreen'
import LembretesScreen from './screens/LembretesScreen'
import { ProfileScreen } from './screens/ProfileScreen'
import { RevisaoScreen } from './screens/RevisaoScreen'
import { AuthScreens } from './screens/AuthScreens'
import { SplashScreen } from './screens/SplashScreen'
import { ConclusionScreen } from './screens/ConclusionScreen'
import { DesignSystemScreen } from './screens/DesignSystemScreen'
import { MeusDadosScreen } from './screens/MeusDadosScreen'
import { AlterarSenhaScreen } from './screens/AlterarSenhaScreen'
import { IgrejasScreen } from './screens/IgrejasScreen'
import { OracoesScreen } from './screens/OracoesScreen'
import { BottomNav } from './components/UI'
import { registrarNavegador } from './services/navigation'
import { rotaExigeConta } from './lib/acesso'
import type { Missa } from './types/missa'

export default function App() {
  const { estaAutenticado, estaCarregando, usuario, logout } = useAuth()
  const [screen, setScreen] = useState('splash')
  const [lastScreen, setLastScreen] = useState('home')
  const [missa, setMissa] = useState<Missa | null>(null)
  const [loginAberto, setLoginAberto] = useState(false)
  const inicioConcluido = useRef(false)
  const requisicaoMissaRef = useRef(0)

  const usuarioNome = usuario?.nome || 'Visitante'

  useEffect(() => {
    if (estaCarregando) return
    if (!inicioConcluido.current) {
      inicioConcluido.current = true
      setScreen('home')
    }
    // Ao entrar ou sair da conta, refaz a seleção. A próxima celebração já
    // montada continua pública; o que exige conta são as demais seções e o
    // acervo de missas passadas.
    void carregarMissa()
  }, [estaCarregando, estaAutenticado])

  // O Mercado Pago retorna ao início após checkout. A pausa do convite só é
  // aplicada quando o webhook já confirmou o apoio como aprovado no servidor.
  useEffect(() => {
    const parametros = new URLSearchParams(window.location.search)
    const apoioId = parametros.get('apoio_id')
    if (parametros.get('apoio') !== 'retorno' || !apoioId) return

    let cancelado = false
    let timer: number | undefined
    let tentativas = 0
    const limparRetorno = () => {
      parametros.delete('apoio')
      parametros.delete('apoio_id')
      const busca = parametros.toString()
      window.history.replaceState({}, '', `${window.location.pathname}${busca ? `?${busca}` : ''}${window.location.hash}`)
    }
    const conferir = async () => {
      try {
        const { data } = await api.get<{ status: string }>(`/apoios/${encodeURIComponent(apoioId)}/status`)
        if (cancelado) return
        if (data.status === 'approved') {
          pausarConviteApoioAposPagamento()
          limparRetorno()
          return
        }
        if (['rejected', 'cancelled', 'failure', 'divergencia_pagamento'].includes(data.status)) {
          limparRetorno()
          return
        }
      } catch {
        if (!cancelado) limparRetorno()
        return
      }
      tentativas += 1
      if (tentativas < 15 && !cancelado) timer = window.setTimeout(conferir, 2000)
      else if (!cancelado) limparRetorno()
    }
    void conferir()
    return () => {
      cancelado = true
      if (timer !== undefined) window.clearTimeout(timer)
    }
  }, [])

  // Toda troca de tela começa pelo topo (não herda scroll da tela anterior).
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior })
    document.documentElement.scrollTop = 0
    document.body.scrollTop = 0
  }, [screen])

  async function carregarMissa() {
    const requisicao = ++requisicaoMissaRef.current
    try {
      const hoje = await getMissaHoje()
      if (requisicao === requisicaoMissaRef.current) setMissa(hoje)
    } catch (e) {
      logError('carregarMissaHoje', e)
      try {
        const proxima = await getProximaMissa()
        const proximaMissa = proxima.montada && proxima.data ? await getMissaPorData(proxima.data) : null
        if (requisicao === requisicaoMissaRef.current) setMissa(proximaMissa)
      } catch (erroProxima) {
        logError('carregarProximaMissaDisponivel', erroProxima)
        if (requisicao === requisicaoMissaRef.current) setMissa(null)
      }
    }
  }

  const navigateTo = useCallback((s: string) => {
    const missaPublica = Boolean(missa?.id)
    // Sem login a missa disponível (hoje ou a próxima já montada) é pública;
    // as demais seções abrem o cadastro.
    if (rotaExigeConta(s, estaAutenticado, missaPublica)) {
      setLoginAberto(true)
      return
    }
    const destino = s
    logNav(screen, destino)
    setLastScreen(screen)
    setScreen(destino)
  }, [screen, estaAutenticado, missa?.data])

  const logoutEVoltarAoInicio = useCallback(async () => {
    await logout()
    setScreen('home')
  }, [logout])

  // Registra a navegação globalmente (usado pela sineta de notificações no AppHeader).
  useEffect(() => { registrarNavegador(navigateTo) }, [navigateTo])

  return (
    <div className="flex flex-col min-h-screen bg-brand-bg dark:bg-slate-900 overflow-x-clip relative">
      <div className="fixed inset-0 opacity-10 pointer-events-none z-0 overflow-hidden">
        <div className="absolute top-[-10%] left-[-5%] w-[60vw] max-w-[400px] aspect-square rounded-full bg-brand-gold blur-3xl" />
        <div className="absolute bottom-[-10%] right-[-5%] w-[70vw] max-w-[500px] aspect-square rounded-full bg-brand-blue blur-3xl" />
      </div>

      <div className="relative z-10 flex flex-col min-h-screen">
        <AnimatePresence mode="wait">
          {screen === 'splash' && <SplashScreen onFinish={() => {}} />}
          {screen === 'home' && <HomeScreen setScreen={navigateTo} missa={missa} nome={usuarioNome} estaAutenticado={estaAutenticado} onLogout={logoutEVoltarAoInicio} />}
          {screen === 'reading' && <ReadingScreen onBack={() => navigateTo('home')} onFinish={() => navigateTo('conclusion')} missaId={missa?.id} registrarProgresso={estaAutenticado} />}
          {screen === 'igrejas' && <IgrejasScreen setScreen={navigateTo} estaAutenticado={estaAutenticado} />}
          {screen === 'oracoes' && <OracoesScreen setScreen={navigateTo} estaAutenticado={estaAutenticado} />}
          {screen === 'calendar' && <CalendarScreen setScreen={navigateTo} estaAutenticado={estaAutenticado} />}
          {screen === 'history' && <JornadaScreen setScreen={navigateTo} />}
          {screen === 'reminders' && (
            <LembretesScreen onBack={() => navigateTo(lastScreen)} />
          )}
          {screen === 'profile' && <ProfileScreen setScreen={navigateTo} usuario={usuario} onLogout={logoutEVoltarAoInicio} />}
          {screen === 'conclusion' && <ConclusionScreen setScreen={navigateTo} missaId={missa?.id} missaData={missa?.data} estaAutenticado={estaAutenticado} />}
          {screen === 'design-system' && <DesignSystemScreen onBack={() => navigateTo('profile')} />}
          {screen === 'meus-dados' && <MeusDadosScreen onBack={() => navigateTo('profile')} />}
          {screen === 'alterar-senha' && <AlterarSenhaScreen onBack={() => navigateTo('profile')} />}
          {screen === 'revisao' && <RevisaoScreen setScreen={navigateTo} />}
        </AnimatePresence>

        <AnimatePresence>
          {loginAberto && (
            <AuthScreens
              setScreen={navigateTo}
              onClose={() => setLoginAberto(false)}
            />
          )}
        </AnimatePresence>

        {!['splash', 'login', 'reading', 'conclusion', 'design-system', 'meus-dados', 'alterar-senha'].includes(screen) && (
          <BottomNav currentScreen={screen} setScreen={navigateTo} estaAutenticado={estaAutenticado} />
        )}
      </div>
    </div>
  )
}
