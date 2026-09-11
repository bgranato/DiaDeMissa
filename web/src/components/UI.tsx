import { ReactNode, useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import { ChevronLeft, ChevronRight, House, Calendar, Bookmark, User, Settings2, ZoomIn, ZoomOut, Contrast, Moon, Sun, List, Church, ScrollText, RotateCcw, MoreHorizontal, Hand, X, Bell } from 'lucide-react';
import { useAccessibility } from '../hooks/useAccessibility';
import api from '../services/api';
import { navegarPara } from '../services/navigation';

// Sineta de notificações GLOBAL — aparece em todas as telas (via AppHeader).
// Busca a contagem de lembretes não-lidos e navega pra tela de lembretes.
export const NotificationBell = () => {
  const [naoLidos, setNaoLidos] = useState(0);
  useEffect(() => {
    api.get<Array<{ lido?: boolean }>>('/usuarios/me/lembretes')
      .then(r => setNaoLidos(r.data.filter(l => !l.lido).length))
      .catch(() => setNaoLidos(0));
  }, []);
  return (
    <button
      onClick={() => navegarPara('reminders')}
      title="Notificações"
      className="p-2.5 rounded-2xl shadow-soft border border-black/5 dark:border-white/5 bg-brand-white dark:bg-slate-800 text-brand-blue dark:text-brand-gold active:scale-95 transition-all"
    >
      <span className="relative inline-flex">
        <Bell size={20} />
        {naoLidos > 0 && (
          <span className="absolute -top-1 -right-1.5 min-w-[16px] h-4 px-1 rounded-full bg-red-500 text-white text-[9px] font-black flex items-center justify-center">
            {naoLidos > 9 ? '9+' : naoLidos}
          </span>
        )}
      </span>
    </button>
  );
};

// Button Component
// LargeButton — usa tokens DS. variant + size = comportamento visual.
// `size="lg"` mantém a altura grande (68px) usada em CTAs primárias da Home/Reading.
export const LargeButton = ({
  onClick,
  children,
  variant = 'primary',
  size = 'lg',
  className = '',
  icon: Icon,
  disabled = false,
}: {
  onClick?: () => void,
  children: ReactNode,
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost',
  size?: 'md' | 'lg',
  className?: string,
  icon?: any,
  disabled?: boolean,
}) => {
  const variantClass = {
    primary: 'ds-btn-primary',
    secondary: 'ds-btn-secondary',
    outline: 'ds-btn-outline',
    ghost: 'ds-btn-ghost',
  }[variant];
  const sizeClass = size === 'lg' ? 'ds-btn-lg' : '';

  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`ds-btn ${variantClass} ${sizeClass} ${className}`}
    >
      {Icon && <Icon size={size === 'lg' ? 22 : 18} />}
      {children}
    </button>
  );
};

// Card Component — usa token .ds-card por default. className só pra ajustes finos.
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
    className={`ds-card ${onClick ? 'cursor-pointer active:scale-[0.98] transition-transform' : ''} ${className}`}
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
  'huge': { idx: 4, label: 'Máximo' },
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
    <div className="relative flex flex-col gap-4 p-5 bg-brand-white/95 dark:bg-slate-800/95 backdrop-blur-xl rounded-[24px] border border-black/5 dark:border-white/10 shadow-strong btn-no-hc">
      {onClose && (
        <button
          onClick={onClose}
          title="Fechar"
          aria-label="Fechar acessibilidade"
          className="absolute top-3 right-3 p-1.5 rounded-full text-brand-gray-dark/60 dark:text-brand-white/60 hover:bg-black/5 dark:hover:bg-white/10 active:scale-90 transition-all"
        >
          <X size={18} />
        </button>
      )}
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
          {/* Indicador visual dos 5 níveis */}
          <div className="flex items-center gap-1 px-3">
            {[0, 1, 2, 3, 4].map(i => (
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
            disabled={nivel.idx === 4}
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
  showNotifications = true,
  rightElement
}: {
  title: string,
  onBack?: () => void,
  showAccessibility?: boolean,
  showNotifications?: boolean,
  rightElement?: ReactNode
}) => {
  const [showControls, setShowControls] = useState(false);
  
  return (
    <header className="sticky top-0 z-30 w-full bg-brand-bg/95 dark:bg-slate-900/95 backdrop-blur-md py-3 border-b border-black/5 dark:border-white/5">
      <div className="ds-container flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {onBack && (
            <button onClick={onBack} aria-label="Voltar"
              className="p-2 -ml-2 text-brand-gray-dark dark:text-brand-white active:scale-90 transition-transform flex-shrink-0">
              <ChevronLeft size={26} />
            </button>
          )}
          {title && (
            <h1 className="ds-headline text-brand-blue dark:text-brand-gold truncate">
              {title}
            </h1>
          )}
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0 -mr-1">
          {rightElement}
          {/* Mesma ordem da Home: acessibilidade (engrenagem) à esquerda, sineta à direita. */}
          {showAccessibility && (
            <button
              onClick={() => setShowControls(!showControls)}
              title={showControls ? 'Fechar acessibilidade' : 'Acessibilidade'}
              className={`p-2.5 rounded-2xl shadow-soft border border-black/5 dark:border-white/5 active:scale-95 transition-all ${showControls ? 'bg-brand-gold text-white' : 'bg-brand-white dark:bg-slate-800 text-brand-blue dark:text-brand-gold'}`}
            >
              <Settings2 size={20} />
            </button>
          )}
          {/* Sineta de notificações — global, aparece em todas as telas (exceto onde desativada). */}
          {showNotifications && <NotificationBell />}
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
            <AccessibilityControls onClose={() => setShowControls(false)} />
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
};

// Ícone de mãos em oração — inspirado em https://www.flaticon.com/free-icon/pray_1526783
// Duas mãos formando "A" no topo (dedos juntos), triângulo aberto no meio (polegares),
// wrists abrindo pros cantos inferiores, raios decorativos.
export const PrayingHandsIcon = ({ size = 24, strokeWidth = 2 }: { size?: number; strokeWidth?: number }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={strokeWidth}
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    {/* Raios decorativos */}
    <line x1="12" y1="1.5" x2="12" y2="3" />
    <line x1="5" y1="3.5" x2="6.5" y2="5" />
    <line x1="19" y1="3.5" x2="17.5" y2="5" />
    <line x1="2" y1="9" x2="4" y2="9" />
    <line x1="22" y1="9" x2="20" y2="9" />

    {/* Mão esquerda — contorno externo: ponta do dedo no topo descendo até o punho */}
    <path d="M11 4 L 5 16 L 6 19 L 9 21 L 11 18.5 L 11 4 Z" />
    {/* Mão direita — espelhada */}
    <path d="M13 4 L 19 16 L 18 19 L 15 21 L 13 18.5 L 13 4 Z" />
    {/* Polegares cruzados — pequena linha horizontal interna */}
    <line x1="10" y1="11" x2="14" y2="11" />
  </svg>
)

// Ícone customizado de padre (figura de clérigo com cruz no peito)
const PadreIcon = ({ size = 24, strokeWidth = 2 }: { size?: number; strokeWidth?: number }) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={strokeWidth}
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden="true"
  >
    {/* Cabeça */}
    <circle cx="12" cy="6" r="3.2" />
    {/* Faixa horizontal na cabeça (biretta/colarinho) */}
    <line x1="9" y1="6.4" x2="15" y2="6.4" />
    {/* Túnica em forma de trapézio */}
    <path d="M5 21 L7.5 11 L16.5 11 L19 21 Z" />
    {/* Cruz central no peito */}
    <line x1="12" y1="13" x2="12" y2="19" />
    <line x1="10" y1="15.5" x2="14" y2="15.5" />
  </svg>
)

// Bottom Navigation
export const BottomNav = ({
  currentScreen,
  setScreen,
  estaAutenticado = true,
}: {
  currentScreen: string,
  setScreen: (s: string) => void,
  estaAutenticado?: boolean,
}) => {
  const [showMais, setShowMais] = useState(false);

  // Itens fixos da barra (4 + botão "Mais")
  const navItems = [
    { id: 'home', label: 'Missa', icon: PadreIcon as any },
    { id: 'igrejas', label: 'Igrejas', icon: Church },
    { id: 'calendar', label: 'Agenda', icon: Calendar },
    { id: 'oracoes', label: 'Orações', icon: PrayingHandsIcon as any },
  ];

  // Menu completo aberto via "Mais"
  const menuCompleto = [
    { id: 'home', label: 'Missa', icon: PadreIcon as any },
    { id: 'igrejas', label: 'Igrejas', icon: Church },
    { id: 'calendar', label: 'Agenda', icon: Calendar },
    { id: 'oracoes', label: 'Orações', icon: PrayingHandsIcon as any },
    ...(estaAutenticado ? [
      { id: 'reminders', label: 'Lembretes', icon: Bell },
      { id: 'history', label: 'Minha Jornada', icon: ScrollText },
      { id: 'profile', label: 'Perfil', icon: User },
    ] : []),
  ];

  function ir(screen: string) {
    setShowMais(false);
    setScreen(screen);
  }

  return (
    <>
      <nav className="fixed bottom-0 left-0 right-0 z-40 bg-brand-gray-dark border-t border-white/5 pb-safe shadow-2xl overflow-hidden">
        <div className="flex justify-around items-center h-20 max-w-lg mx-auto px-1">
          {navItems.map((item) => (
            <button
              key={item.id}
              onClick={() => setScreen(item.id)}
              className={`flex-1 min-w-0 flex flex-col items-center gap-1 px-1 py-2 transition-all duration-300 ${
                currentScreen === item.id
                  ? 'opacity-100 text-brand-gold scale-105'
                  : 'opacity-40 text-white'
              }`}
            >
              <item.icon size={22} strokeWidth={currentScreen === item.id ? 2.5 : 2} />
              <span className="text-[9px] uppercase font-black tracking-wider truncate max-w-full">{item.label}</span>
            </button>
          ))}
          {/* Botão Mais */}
          <button
            onClick={() => setShowMais(true)}
            className={`flex-1 min-w-0 flex flex-col items-center gap-1 px-1 py-2 transition-all duration-300 ${
              showMais || ['history', 'profile'].includes(currentScreen)
                ? 'opacity-100 text-brand-gold scale-105'
                : 'opacity-40 text-white'
            }`}
          >
            <MoreHorizontal size={22} strokeWidth={showMais ? 2.5 : 2} />
            <span className="text-[9px] uppercase font-black tracking-wider truncate max-w-full">Mais</span>
          </button>
        </div>
      </nav>

      {/* Drawer Mais — bottom sheet com menu completo */}
      <AnimatePresence>
        {showMais && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 bg-black/50 flex items-end justify-center"
            onClick={() => setShowMais(false)}>
            <motion.div
              initial={{ y: 40 }} animate={{ y: 0 }} exit={{ y: 40 }}
              className="bg-white dark:bg-slate-900 rounded-t-[32px] w-full max-w-lg pb-safe"
              onClick={e => e.stopPropagation()}>
              <div className="flex items-center justify-between px-6 pt-5 pb-3">
                <h3 className="text-lg font-serif font-black text-brand-blue dark:text-brand-white">Menu</h3>
                <button onClick={() => setShowMais(false)} className="p-2 rounded-full hover:bg-gray-100 dark:hover:bg-slate-800">
                  <X size={20} />
                </button>
              </div>
              <div className="menu-mais-grid grid grid-cols-3 gap-3 px-6 pb-8 pt-3">
                {menuCompleto.map(item => (
                  <button key={item.id} onClick={() => ir(item.id)}
                    className={`flex flex-col items-center gap-2 p-[16px] rounded-2xl transition-all active:scale-[0.96] ${
                      currentScreen === item.id
                        ? 'bg-brand-gold/15 border-2 border-brand-gold'
                        : 'bg-brand-bg dark:bg-slate-800 border-2 border-transparent'
                    }`}>
                    <div className={`p-[12px] rounded-xl ${currentScreen === item.id ? 'bg-brand-gold text-white' : 'bg-brand-blue dark:bg-brand-gold text-white dark:text-brand-blue'}`}>
                      <item.icon size={22} />
                    </div>
                    <span className="text-[13px] font-black text-brand-gray-dark dark:text-brand-white text-center leading-tight [overflow-wrap:normal] [word-break:normal] hyphens-none">{item.label}</span>
                  </button>
                ))}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

