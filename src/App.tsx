/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import { useState } from 'react';
import { AnimatePresence } from 'motion/react';
import { HomeScreen } from './screens/HomeScreen';
import { ReadingScreen } from './screens/ReadingScreen';
import { CalendarScreen } from './screens/CalendarScreen';
import { HistoryScreen } from './screens/HistoryScreen';
import { RemindersScreen } from './screens/RemindersScreen';
import { ProfileScreen } from './screens/ProfileScreen';
import { AuthScreens } from './screens/AuthScreens';
import { SplashScreen } from './screens/SplashScreen';
import { ConclusionScreen } from './screens/ConclusionScreen';
import { DesignSystemScreen } from './screens/DesignSystemScreen';
import { BottomNav } from './components/UI';
import { MOCK_REMINDERS } from './data/mockMass';

export default function App() {
  const [screen, setScreen] = useState('splash');
  const [lastScreen, setLastScreen] = useState('home');
  const [reminders, setReminders] = useState(MOCK_REMINDERS);

  const navigateTo = (s: string) => {
    setLastScreen(screen);
    setScreen(s);
  };

  const toggleReminder = (id: string) => {
    setReminders(prev => prev.map(r => r.id === id ? { ...r, ativo: !r.ativo } : r));
  };

  const markAsSeen = (id: string) => {
    setReminders(prev => prev.map(r => r.id === id ? { ...r, visto: true } : r));
  };

  const renderScreen = () => {
    switch (screen) {
      case 'home':
        return <HomeScreen setScreen={navigateTo} reminders={reminders} />;
      case 'reading':
        return <ReadingScreen onBack={() => navigateTo('home')} onFinish={() => navigateTo('conclusion')} />;
      case 'calendar':
        return <CalendarScreen setScreen={navigateTo} />;
      case 'history':
        return <HistoryScreen setScreen={navigateTo} />;
      case 'reminders':
        return <RemindersScreen reminders={reminders} toggleReminder={toggleReminder} markAsSeen={markAsSeen} onBack={() => navigateTo(lastScreen)} />;
      case 'profile':
        return <ProfileScreen setScreen={navigateTo} />;
      case 'login':
        return <AuthScreens setScreen={navigateTo} />;
      case 'conclusion':
        return <ConclusionScreen setScreen={navigateTo} />;
      case 'design-system':
        return <DesignSystemScreen onBack={() => navigateTo('profile')} />;
      case 'splash':
        return <SplashScreen onFinish={() => setScreen('login')} />;
      default:
        return <HomeScreen setScreen={navigateTo} reminders={reminders} />;
    }
  };

  // Screens that should NOT show the bottom navigation
  const hideNav = ['splash', 'login', 'reading', 'conclusion', 'design-system'].includes(screen);

  return (
    <div className="flex flex-col min-h-screen bg-brand-bg dark:bg-slate-900 overflow-x-hidden relative">
      {/* Background Decoration */}
      <div className="fixed inset-0 opacity-10 pointer-events-none z-0">
        <div className="absolute top-[-10%] left-[-5%] w-[400px] h-[400px] rounded-full bg-brand-gold blur-3xl"></div>
        <div className="absolute bottom-[-10%] right-[-5%] w-[500px] h-[500px] rounded-full bg-brand-blue blur-3xl"></div>
      </div>

      <div className="relative z-10 flex flex-col min-h-screen">
        <AnimatePresence mode="wait">
          {renderScreen()}
        </AnimatePresence>

        {!hideNav && (
          <BottomNav currentScreen={screen} setScreen={navigateTo} />
        )}
      </div>
    </div>
  );
}
