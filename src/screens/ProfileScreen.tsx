import { motion } from 'motion/react';
import { AppHeader, Card } from '../components/UI';
import { User, LogOut, Settings, History, Bell, ChevronRight, Sun, Moon, Contrast, Layout, ZoomIn, ZoomOut } from 'lucide-react';
import { useAccessibility } from '../hooks/useAccessibility';

export const ProfileScreen = ({ setScreen }: { setScreen: (s: string) => void }) => {
  const { toggleDarkMode, toggleHighContrast, increaseFontSize, decreaseFontSize, prefs } = useAccessibility();

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="pb-32"
    >
      <AppHeader title="Meu Perfil" showAccessibility={false} />
      
      <div className="p-6 flex flex-col gap-8 max-w-lg mx-auto">
        <div className="flex flex-col items-center gap-4 text-center py-8">
          <div className="w-28 h-28 bg-brand-gold rounded-full flex items-center justify-center text-brand-white shadow-strong border-[6px] border-brand-white dark:border-slate-800">
            <User size={56} />
          </div>
          <div>
            <h3 className="text-3xl font-serif font-black text-brand-gray-dark dark:text-brand-white">João da Silva</h3>
            <p className="text-brand-blue font-bold opacity-60">joao.silva@email.com</p>
          </div>
          <button className="text-brand-gold font-black text-xs uppercase tracking-[0.2em] bg-brand-gold/10 px-6 py-3 rounded-2xl active:scale-95 transition-transform">
            Editar perfil
          </button>
        </div>

        <div className="flex flex-col gap-4">
          <h4 className="font-bold text-brand-gray-dark/40 dark:text-brand-white/40 uppercase text-[10px] tracking-[0.3em] ml-2">Acessibilidade e Layout</h4>
          
          <div className="grid grid-cols-2 gap-4 mb-4">
             <button 
              onClick={toggleDarkMode}
              className={`flex flex-col items-center gap-3 p-6 rounded-[32px] border-2 transition-all active:scale-95 ${prefs.darkMode ? 'bg-brand-gray-dark border-brand-gray-dark text-brand-white' : 'bg-brand-white border-black/5 dark:bg-slate-800 dark:text-brand-white shadow-soft'}`}
            >
              <div className={`p-4 rounded-2xl ${prefs.darkMode ? 'bg-brand-white/10' : 'bg-brand-gray-dark/5'}`}>
                {prefs.darkMode ? <Sun size={28} /> : <Moon size={28} />}
              </div>
              <span className="font-black text-xs uppercase tracking-widest">Escuro</span>
            </button>
            <button 
              onClick={toggleHighContrast}
              className={`flex flex-col items-center gap-3 p-6 rounded-[32px] border-2 transition-all active:scale-95 ${prefs.highContrast ? 'bg-brand-gold border-brand-gold text-brand-white' : 'bg-brand-white border-black/5 dark:bg-slate-800 dark:text-brand-white shadow-soft'}`}
            >
              <div className={`p-4 rounded-2xl ${prefs.highContrast ? 'bg-brand-white/20' : 'bg-brand-gray-dark/5'}`}>
                <Contrast size={28} />
              </div>
              <span className="font-black text-xs uppercase tracking-widest">Brilho</span>
            </button>
          </div>

          <div className="flex gap-4 mb-8">
            <button 
              onClick={decreaseFontSize}
              className="flex-1 flex flex-col items-center gap-2 p-6 bg-brand-white dark:bg-slate-800 rounded-[32px] border-2 border-black/5 shadow-soft active:scale-95"
            >
              <ZoomOut size={28} className="text-brand-blue dark:text-brand-gold" />
              <span className="font-black text-xs uppercase tracking-widest">A- Texto</span>
            </button>
            <button 
              onClick={increaseFontSize}
              className="flex-1 flex flex-col items-center gap-2 p-6 bg-brand-white dark:bg-slate-800 rounded-[32px] border-2 border-black/5 shadow-soft active:scale-95"
            >
              <ZoomIn size={28} className="text-brand-blue dark:text-brand-gold" />
              <span className="font-black text-xs uppercase tracking-widest">A+ Texto</span>
            </button>
          </div>

          <h4 className="font-bold text-brand-gray-dark/40 dark:text-brand-white/40 uppercase text-[10px] tracking-[0.3em] ml-2">Configurações</h4>
          
          <Card className="p-2 flex flex-col divide-y divide-black/5 dark:divide-slate-700 dark:bg-slate-800 border-none shadow-soft">
            <button 
              onClick={() => setScreen('history')}
              className="flex items-center gap-5 p-5 active:bg-brand-bg dark:active:bg-slate-700 text-left transition-colors first:rounded-t-[28px]"
            >
              <div className="p-3 bg-brand-gold/[0.08] text-brand-gold rounded-2xl">
                <History size={24} />
              </div>
              <span className="flex-1 font-black text-brand-gray-dark dark:text-brand-white">Meus Registros</span>
              <ChevronRight size={24} className="text-black/10" />
            </button>
            <button 
              onClick={() => setScreen('reminders')}
              className="flex items-center gap-5 p-5 active:bg-brand-bg dark:active:bg-slate-700 text-left transition-colors"
            >
              <div className="p-3 bg-brand-blue/[0.08] text-brand-blue rounded-2xl">
                <Bell size={24} />
              </div>
              <span className="flex-1 font-black text-brand-gray-dark dark:text-brand-white">Meus Lembretes</span>
              <ChevronRight size={24} className="text-black/10" />
            </button>
            <button 
              onClick={() => setScreen('design-system')}
              className="flex items-center gap-5 p-5 active:bg-brand-bg dark:active:bg-slate-700 text-left transition-colors last:rounded-b-[28px]"
            >
              <div className="p-3 bg-brand-gold/[0.08] text-brand-gold rounded-2xl">
                <Layout size={24} />
              </div>
              <span className="flex-1 font-black text-brand-gray-dark dark:text-brand-white">Design System</span>
              <ChevronRight size={24} className="text-black/10" />
            </button>
          </Card>

          <h4 className="font-bold text-brand-gray-dark/40 dark:text-brand-white/40 uppercase text-[10px] tracking-[0.3em] ml-2 mt-4">Preferências Visuais</h4>
          
          <div className="grid grid-cols-2 gap-4">
             <button 
              onClick={toggleDarkMode}
              className={`flex flex-col items-center gap-3 p-6 rounded-[32px] border-2 transition-all active:scale-95 ${prefs.darkMode ? 'bg-brand-gray-dark border-brand-gray-dark text-brand-white' : 'bg-brand-white border-black/5 dark:bg-slate-800 dark:text-brand-white shadow-soft'}`}
            >
              <div className={`p-4 rounded-2xl ${prefs.darkMode ? 'bg-brand-white/10' : 'bg-brand-gray-dark/5'}`}>
                {prefs.darkMode ? <Sun size={28} /> : <Moon size={28} />}
              </div>
              <span className="font-black text-xs uppercase tracking-widest">Escuro</span>
            </button>
            <button 
              onClick={toggleHighContrast}
              className={`flex flex-col items-center gap-3 p-6 rounded-[32px] border-2 transition-all active:scale-95 ${prefs.highContrast ? 'bg-brand-gold border-brand-gold text-brand-white' : 'bg-brand-white border-black/5 dark:bg-slate-800 dark:text-brand-white shadow-soft'}`}
            >
              <div className={`p-4 rounded-2xl ${prefs.highContrast ? 'bg-brand-white/20' : 'bg-brand-gray-dark/5'}`}>
                <Contrast size={28} />
              </div>
              <span className="font-black text-xs uppercase tracking-widest">Brilho</span>
            </button>
          </div>
          
          <button 
            onClick={() => setScreen('login')}
            className="mt-8 flex items-center justify-center gap-3 p-6 text-red-600 font-black uppercase tracking-[0.2em] text-sm bg-red-50 dark:bg-red-900/20 rounded-[32px] active:scale-[0.98] transition-transform"
          >
            <LogOut size={24} /> Sair do App
          </button>
        </div>
      </div>
    </motion.div>
  );
};
