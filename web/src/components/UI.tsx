import { ReactNode, useState } from 'react';
import { motion } from 'motion/react';
import { ChevronLeft, ChevronRight, House, Calendar, Bookmark, User, Settings2, ZoomIn, ZoomOut, Contrast, Moon, Sun, List, Church, ScrollText, RotateCcw } from 'lucide-react';
import { useAccessibility } from '../hooks/useAccessibility';

// Button Component
export const LargeButton = ({ 
  onClick, 
  children, 
  variant = 'primary', 
  className = '',
  icon: Icon,
  disabled = false
}: { 
  onClick?: () => void, 
  children: ReactNode, 
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost',
  className?: string,
  icon?: any,
  disabled?: boolean
}) => {
  const baseStyles = "flex items-center justify-center gap-3 px-8 py-5 rounded-[24px] font-bold text-lg transition-all active:scale-95 shadow-soft min-h-[68px]";
  
  const variants = {
    primary: "bg-brand-blue text-white hover:opacity-95",
    secondary: "bg-brand-gold text-white hover:opacity-95 shadow-strong",
    outline: "border-2 border-brand-blue text-brand-blue hover:bg-brand-blue/5",
    ghost: "text-brand-gray-dark hover:bg-black/5"
  };

  return (
    <button 
      onClick={onClick} 
      disabled={disabled}
      className={`${baseStyles} ${variants[variant]} ${className} ${disabled ? 'opacity-40 grayscale' : ''}`}
    >
      {Icon && <Icon size={24} />}
      {children}
    </button>
  );
};

// Card Component
export interface CardProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
  [key: string]: any;
}

export const Card = ({ children, className = '', onClick, ...props }: CardProps) => (
  <div 
    {...props}
    onClick={onClick}
    className={`bg-brand-white rounded-[32px] p-8 shadow-soft border border-black/5 ${onClick ? 'cursor-pointer active:scale-[0.98]' : ''} ${className}`}
  >
    {children}
  </div>
);

// Accessibility Controls Component
const FONT_LEVELS: Record<string, { idx: number; label: string }> = {
  'small': { idx: 0, label: 'Pequeno' },
  'medium': { idx: 1, label: 'Padrão' },
  'large': { idx: 2, label: 'Grande' },
  'extra-large': { idx: 3, label: 'Muito grande' },
};

export const AccessibilityControls = ({
  onClose,
}: {
  onClose?: () => void
}) => {
  const {
    prefs,
    increaseFontSize,
    decreaseFontSize,
    resetFontSize,
    toggleDarkMode,
    toggleHighContrast,
  } = useAccessibility();

  const nivel = FONT_LEVELS[prefs.fontSize] || FONT_LEVELS.medium;
  const isPadrao = prefs.fontSize === 'medium';

  return (
    <div className="flex flex-col gap-4 p-5 bg-brand-white/95 dark:bg-slate-800/95 backdrop-blur-xl rounded-[24px] border border-black/5 dark:border-white/10 shadow-strong btn-no-hc">
      {/* Fonte */}
      <div>
        <p className="text-[10px] font-black uppercase tracking-[0.2em] text-brand-gray-dark/60 dark:text-brand-white/60 mb-2">
          Tamanho do texto · {nivel.label}
        </p>
        <div className="flex gap-2 items-stretch">
          <button
            onClick={decreaseFontSize}
            disabled={nivel.idx === 0}
            className="flex-1 flex items-center justify-center gap-1 p-3 bg-brand-gray-dark/5 dark:bg-slate-700 rounded-2xl text-brand-gray-dark dark:text-brand-white active:scale-95 transition-all disabled:opacity-30"
            title="Diminuir fonte"
          >
            <ZoomOut size={20} />
            <span className="text-xs font-black">A-</span>
          </button>
          {/* Indicador visual dos 4 níveis */}
          <div className="flex items-center gap-1 px-3">
            {[0, 1, 2, 3].map(i => (
              <span
                key={i}
                className={`h-2 rounded-full transition-all ${
                  i === nivel.idx
                    ? 'w-6 bg-brand-gold'
                    : 'w-2 bg-brand-gray-dark/15 dark:bg-white/15'
                }`}
              />
            ))}
          </div>
          <button
            onClick={increaseFontSize}
            disabled={nivel.idx === 3}
            className="flex-1 flex items-center justify-center gap-1 p-3 bg-brand-gray-dark/5 dark:bg-slate-700 rounded-2xl text-brand-gray-dark dark:text-brand-white active:scale-95 transition-all disabled:opacity-30"
            title="Aumentar fonte"
          >
            <ZoomIn size={20} />
            <span className="text-xs font-black">A+</span>
          </button>
          <button
            onClick={resetFontSize}
            disabled={isPadrao}
            className="flex items-center justify-center gap-1 px-3 py-3 bg-brand-gray-dark/5 dark:bg-slate-700 rounded-2xl text-brand-gray-dark dark:text-brand-white active:scale-95 transition-all disabled:opacity-30"
            title="Voltar ao tamanho padrão"
          >
            <RotateCcw size={18} />
          </button>
        </div>
      </div>

      {/* Modos visuais */}
      <div>
        <p className="text-[10px] font-black uppercase tracking-[0.2em] text-brand-gray-dark/60 dark:text-brand-white/60 mb-2">
          Modo visual
        </p>
        <div className="flex gap-2">
          <button
            onClick={toggleDarkMode}
            aria-pressed={prefs.darkMode}
            className={`flex-1 flex flex-col items-center gap-1.5 p-3 rounded-2xl active:scale-95 transition-all border-2 ${
              prefs.darkMode
                ? 'bg-brand-blue text-white border-brand-gold ring-2 ring-brand-gold/40'
                : 'bg-brand-gray-dark/5 dark:bg-slate-700 text-brand-gray-dark dark:text-brand-white border-transparent'
            }`}
            title="Modo Escuro"
          >
            {prefs.darkMode ? <Sun size={22} /> : <Moon size={22} />}
            <span className="text-[10px] font-black uppercase tracking-widest">
              Escuro {prefs.darkMode && '·on'}
            </span>
          </button>
          <button
            onClick={toggleHighContrast}
            aria-pressed={prefs.highContrast}
            className={`flex-1 flex flex-col items-center gap-1.5 p-3 rounded-2xl active:scale-95 transition-all border-2 ${
              prefs.highContrast
                ? 'bg-yellow-300 text-black border-black ring-2 ring-yellow-500/60'
                : 'bg-brand-gray-dark/5 dark:bg-slate-700 text-brand-gray-dark dark:text-brand-white border-transparent'
            }`}
            title="Alto Contraste"
          >
            <Contrast size={22} />
            <span className="text-[10px] font-black uppercase tracking-widest">
              Brilho {prefs.highContrast && '·on'}
            </span>
          </button>
        </div>
      </div>
    </div>
  );
};

// Top Header
export const AppHeader = ({ 
  title, 
  onBack, 
  showAccessibility = true,
  rightElement
}: { 
  title: string, 
  onBack?: () => void,
  showAccessibility?: boolean,
  rightElement?: ReactNode
}) => {
  const [showControls, setShowControls] = useState(false);
  
  return (
    <header className="sticky top-0 z-30 w-full bg-brand-bg/90 dark:bg-slate-900/90 backdrop-blur-md px-5 py-4 border-b border-black/5">
      <div className="flex items-center justify-between gap-4 max-w-xl mx-auto">
        <div className="flex items-center gap-4">
          {onBack && (
            <button onClick={onBack} className="p-2 -ml-2 text-brand-gray-dark dark:text-brand-white active:scale-90 transition-transform">
              <ChevronLeft size={32} />
            </button>
          )}
          <div className="flex flex-col">
            <h1 className="text-2xl font-serif font-black text-brand-blue dark:text-brand-gold tracking-tight truncate">
              {title}
            </h1>
            {title === 'Missa Hoje' && (
              <p className="text-[10px] uppercase tracking-[0.3em] text-brand-gold font-black">Liturgia Diária</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {rightElement}
          {showAccessibility && (
            <button 
              onClick={() => setShowControls(!showControls)}
              className={`p-3 rounded-2xl transition-all shadow-soft ${showControls ? 'bg-brand-gold text-white scale-110' : 'bg-brand-white text-brand-gray-dark'}`}
            >
              <Settings2 size={24} />
            </button>
          )}
        </div>
      </div>
      
      <AnimatePresence>
        {showControls && (
          <motion.div 
            initial={{ opacity: 0, y: -10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -10, scale: 0.95 }}
            className="max-w-lg mx-auto mt-6"
          >
            <AccessibilityControls />
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
};

import { AnimatePresence } from 'motion/react';

// Bottom Navigation
export const BottomNav = ({ 
  currentScreen, 
  setScreen 
}: { 
  currentScreen: string, 
  setScreen: (s: string) => void 
}) => {
  const navItems = [
    { id: 'home', label: 'Missa', icon: Church },
    { id: 'calendar', label: 'Agenda', icon: Calendar },
    { id: 'history', label: 'Histórico', icon: ScrollText },
    { id: 'profile', label: 'Perfil', icon: User },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-40 bg-brand-gray-dark border-t border-white/5 pb-safe shadow-2xl">
      <div className="flex justify-around items-center h-20 max-w-lg mx-auto px-2">
        {navItems.map((item) => (
          <button
            key={item.id}
            onClick={() => setScreen(item.id)}
            className={`flex flex-col items-center gap-1.5 px-4 py-2 transition-all duration-300 ${
              currentScreen === item.id 
              ? 'opacity-100 text-brand-gold scale-110' 
              : 'opacity-40 text-white'
            }`}
          >
            <item.icon size={26} strokeWidth={currentScreen === item.id ? 2.5 : 2} />
            <span className="text-[10px] uppercase font-black tracking-[0.2em]">{item.label}</span>
          </button>
        ))}
      </div>
    </nav>
  );
};


