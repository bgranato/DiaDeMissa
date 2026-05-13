import { useState, useEffect, useCallback } from 'react'
import { AnimatePresence } from 'motion/react'
import { useAuth } from './contexts/AuthContext'
import { getMissaHoje } from './services/missa'
import { logNav, logError } from './services/logger'
import { HomeScreen } from './screens/HomeScreen'
import { ReadingScreen } from './screens/ReadingScreen'
import { CalendarScreen } from './screens/CalendarScreen'
import { HistoryScreen } from './screens/HistoryScreen'
import LembretesScreen from './screens/LembretesScreen'
import { ProfileScreen } from './screens/ProfileScreen'
import { AuthScreens } from './screens/AuthScreens'
import { SplashScreen } from './screens/SplashScreen'
import { ConclusionScreen } from './screens/ConclusionScreen'
import { DesignSystemScreen } from './screens/DesignSystemScreen'
import { MeusDadosScreen } from './screens/MeusDadosScreen'
import { AlterarSenhaScreen } from './screens/AlterarSenhaScreen'
import { BottomNav } from './components/UI'
import type { Missa } from './types/missa'

export default function App() {
  const { estaAutenticado, estaCarregando, usuario, logout } = useAuth()
  const [screen, setScreen] = useState('splash')
  const [lastScreen, setLastScreen] = useState('home')
  const [missa, setMissa] = useState<Missa | null>(null)

  const usuarioNome = usuario?.nome || 'Fiel'

  useEffect(() => {
    if (estaCarregando) return
    if (!estaAutenticado) {
      setScreen('login')
      return
    }
    setScreen('home')
    carregarMissa()
  }, [estaCarregando, estaAutenticado])

  async function carregarMissa() {
    try {
      setMissa(await getMissaHoje())
    } catch (e) {
      logError('carregarMissaHoje', e)
      setMissa(null)
    }
  }

  const navigateTo = useCallback((s: string) => {
    logNav(screen, s)
    setLastScreen(screen)
    setScreen(s)
  }, [screen])

  return (
    <div className="flex flex-col min-h-screen bg-brand-bg dark:bg-slate-900 overflow-x-hidden relative">
      <div className="fixed inset-0 opacity-10 pointer-events-none z-0">
        <div className="absolute top-[-10%] left-[-5%] w-[400px] h-[400px] rounded-full bg-brand-gold blur-3xl" />
        <div className="absolute bottom-[-10%] right-[-5%] w-[500px] h-[500px] rounded-full bg-brand-blue blur-3xl" />
      </div>

      <div className="relative z-10 flex flex-col min-h-screen">
        <AnimatePresence mode="wait">
          {screen === 'splash' && <SplashScreen onFinish={() => {}} />}
          {screen === 'login' && <AuthScreens setScreen={navigateTo} />}
          {screen === 'home' && <HomeScreen setScreen={navigateTo} missa={missa} nome={usuarioNome} onLogout={logout} />}
          {screen === 'reading' && <ReadingScreen onBack={() => navigateTo('home')} onFinish={() => navigateTo('conclusion')} missaId={missa?.id} />}
          {screen === 'calendar' && <CalendarScreen setScreen={navigateTo} />}
          {screen === 'history' && <HistoryScreen setScreen={navigateTo} />}
          {screen === 'reminders' && (
            <LembretesScreen onBack={() => navigateTo(lastScreen)} />
          )}
          {screen === 'profile' && <ProfileScreen setScreen={navigateTo} usuario={usuario} onLogout={logout} />}
          {screen === 'conclusion' && <ConclusionScreen setScreen={navigateTo} />}
          {screen === 'design-system' && <DesignSystemScreen onBack={() => navigateTo('profile')} />}
          {screen === 'meus-dados' && <MeusDadosScreen onBack={() => navigateTo('profile')} />}
          {screen === 'alterar-senha' && <AlterarSenhaScreen onBack={() => navigateTo('profile')} />}
        </AnimatePresence>

        {!['splash', 'login', 'reading', 'conclusion', 'design-system', 'meus-dados', 'alterar-senha'].includes(screen) && (
          <BottomNav currentScreen={screen} setScreen={navigateTo} />
        )}
      </div>
    </div>
  )
}
