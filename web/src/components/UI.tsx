import { ReactNode, useState } from 'react';
import { motion } from 'motion/react';
import { ChevronLeft, ChevronRight, House, Calendar, Bookmark, User, Settings2, ZoomIn, ZoomOut, Contrast, Moon, Sun, List } from 'lucide-react';
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
export const AccessibilityControls = ({ 
  onClose 
}: { 
  onClose?: () => void 
}) => {
  const { 
    prefs, 
    increaseFontSize, 
    decreaseFontSize, 
    toggleDarkMode, 
    toggleHighContrast 
  } = useAccessibility();

  return (
    <div className="flex flex-wrap gap-3 p-5 bg-brand-white/80 backdrop-blur-xl rounded-[24px] border border-black/5 shadow-strong">
      <button 
        onClick={decreaseFontSize}
        className="flex-1 flex flex-col items-center gap-2 p-4 bg-brand-gray-dark/5 rounded-2xl text-brand-gray-dark active:scale-95 transition-all"
        title="Diminuir fonte"
      >
        <ZoomOut size={24} />
        <span className="text-[10px] font-black uppercase tracking-widest">A-</span>
      </button>
      <button 
        onClick={increaseFontSize}
        className="flex-1 flex flex-col items-center gap-2 p-4 bg-brand-blue text-brand-white rounded-2xl active:scale-95 transition-all"
        title="Aumentar fonte"
      >
        <ZoomIn size={24} />
        <span className="text-[10px] font-black uppercase tracking-widest">A+</span>
      </button>
      <button 
        onClick={toggleDarkMode}
        className={`flex-1 flex flex-col items-center gap-2 p-4 rounded-2xl active:scale-95 transition-all ${prefs.darkMode ? 'bg-brand-gray-dark text-brand-white' : 'bg-brand-gray-dark/5 text-brand-gray-dark'}`}
        title="Modo Escuro"
      >
        {prefs.darkMode ? <Sun size={24} /> : <Moon size={24} />}
        <span className="text-[10px] font-black uppercase tracking-widest">Escuro</span>
      </button>
      <button 
        onClick={toggleHighContrast}
        className={`flex-1 flex flex-col items-center gap-2 p-4 rounded-2xl active:scale-95 transition-all ${prefs.highContrast ? 'bg-brand-gold text-brand-white' : 'bg-brand-gray-dark/5 text-brand-gray-dark'}`}
        title="Alto Contraste"
      >
        <Contrast size={24} />
        <span className="text-[10px] font-black uppercase tracking-widest">Brilho</span>
      </button>
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
    <header className="sticky top-0 z-30 w-full bg-brand-bg/90 dark:bg-slate-900/90 backdrop-blur-md px-6 py-4 border-b border-black/5">
      <div className="flex items-center justify-between gap-4 max-w-lg mx-auto">
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
    { id: 'home', label: 'Missa', icon: House },
    { id: 'calendar', label: 'Agenda', icon: Calendar },
    { id: 'history', label: 'Histórico', icon: Bookmark },
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


