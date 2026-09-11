import { useState, useEffect, useCallback } from 'react'
import { AnimatePresence } from 'motion/react'
import { useAuth } from './contexts/AuthContext'
import { getMissaHoje } from './services/missa'
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
import type { Missa } from './types/missa'

export default function App() {
  const { estaAutenticado, estaCarregando, usuario, logout } = useAuth()
  const [screen, setScreen] = useState('splash')
  const [lastScreen, setLastScreen] = useState('home')
  const [missa, setMissa] = useState<Missa | null>(null)

  const usuarioNome = usuario?.nome || 'Visitante'

  useEffect(() => {
    if (estaCarregando) return
    setScreen('home')
    carregarMissa()
  }, [estaCarregando, estaAutenticado])

  // Toda troca de tela começa pelo topo (não herda scroll da tela anterior).
  useEffect(() => {
    window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior })
    document.documentElement.scrollTop = 0
    document.body.scrollTop = 0
  }, [screen])

  async function carregarMissa() {
    try {
      setMissa(await getMissaHoje())
    } catch (e) {
      logError('carregarMissaHoje', e)
      setMissa(null)
    }
  }

  const navigateTo = useCallback((s: string) => {
    // A celebração, o calendário, as orações e a busca de igrejas são públicos.
    // Login continua sendo exigido apenas quando a pessoa escolhe um recurso que
    // guarda dados pessoais (histórico, lembretes, perfil ou revisão).
    const exigeConta = ['history', 'reminders', 'profile', 'meus-dados', 'alterar-senha', 'revisao'].includes(s)
    const destino = exigeConta && !estaAutenticado ? 'login' : s
    logNav(screen, destino)
    setLastScreen(screen)
    setScreen(destino)
  }, [screen, estaAutenticado])

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
          {screen === 'login' && <AuthScreens setScreen={navigateTo} />}
          {screen === 'home' && <HomeScreen setScreen={navigateTo} missa={missa} nome={usuarioNome} estaAutenticado={estaAutenticado} onLogout={logout} />}
          {screen === 'reading' && <ReadingScreen onBack={() => navigateTo('home')} onFinish={() => navigateTo('conclusion')} missaId={missa?.id} registrarProgresso={estaAutenticado} />}
          {screen === 'igrejas' && <IgrejasScreen setScreen={navigateTo} estaAutenticado={estaAutenticado} />}
          {screen === 'oracoes' && <OracoesScreen setScreen={navigateTo} estaAutenticado={estaAutenticado} />}
          {screen === 'calendar' && <CalendarScreen setScreen={navigateTo} estaAutenticado={estaAutenticado} />}
          {screen === 'history' && <JornadaScreen setScreen={navigateTo} />}
          {screen === 'reminders' && (
            <LembretesScreen onBack={() => navigateTo(lastScreen)} />
          )}
          {screen === 'profile' && <ProfileScreen setScreen={navigateTo} usuario={usuario} onLogout={logout} />}
          {screen === 'conclusion' && <ConclusionScreen setScreen={navigateTo} missaId={missa?.id} missaData={missa?.data} estaAutenticado={estaAutenticado} />}
          {screen === 'design-system' && <DesignSystemScreen onBack={() => navigateTo('profile')} />}
          {screen === 'meus-dados' && <MeusDadosScreen onBack={() => navigateTo('profile')} />}
          {screen === 'alterar-senha' && <AlterarSenhaScreen onBack={() => navigateTo('profile')} />}
          {screen === 'revisao' && <RevisaoScreen setScreen={navigateTo} />}
        </AnimatePresence>

        {!['splash', 'login', 'reading', 'conclusion', 'design-system', 'meus-dados', 'alterar-senha'].includes(screen) && (
          <BottomNav currentScreen={screen} setScreen={navigateTo} estaAutenticado={estaAutenticado} />
        )}
      </div>
    </div>
  )
}
