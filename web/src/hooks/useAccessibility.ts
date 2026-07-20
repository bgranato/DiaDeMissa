import { useState, useEffect } from 'react';
import { UserPreferences } from '../types/usuario';

export function useAccessibility() {
  const [prefs, setPrefs] = useState<UserPreferences>(() => {
    const saved = localStorage.getItem('missa_hoje_prefs');
    // Lê o localStorage como está. O reset "novo acesso → padrão" é feito UMA VEZ
    // no boot (main.tsx), que já grava fontSize='medium'. Aqui NÃO forçamos medium,
    // senão o ajuste feito na sessão sumiria a cada remontagem (ex.: fechar a config).
    if (saved) return JSON.parse(saved);
    return {
      fontSize: 'medium',
      highContrast: false,
      darkMode: false,
    };
  });

  useEffect(() => {
    localStorage.setItem('missa_hoje_prefs', JSON.stringify(prefs));
    
    // Apply dark mode or high contrast to document
    if (prefs.darkMode) {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
    } else {
      document.documentElement.classList.remove('dark');
      document.documentElement.classList.add('light');
    }
    
    if (prefs.highContrast) {
      document.documentElement.classList.add('high-contrast');
    } else {
      document.documentElement.classList.remove('high-contrast');
    }

    // Apply font size logic to document root
    const rootFontSizeMap = {
      'small': '90%',
      'medium': '100%',
      'large': '115%',
      'extra-large': '130%',
      'huge': '150%',
    };
    document.documentElement.style.fontSize = rootFontSizeMap[prefs.fontSize];
    document.documentElement.setAttribute('data-font-size', prefs.fontSize);
  }, [prefs]);

  const toggleDarkMode = () => setPrefs(prev => ({ ...prev, darkMode: !prev.darkMode, highContrast: false }));
  const toggleHighContrast = () => setPrefs(prev => ({ ...prev, highContrast: !prev.highContrast, darkMode: false }));

  const SIZES: UserPreferences['fontSize'][] = ['small', 'medium', 'large', 'extra-large', 'huge'];

  const increaseFontSize = () => {
    const currentIndex = SIZES.indexOf(prefs.fontSize);
    if (currentIndex < SIZES.length - 1) {
      setPrefs(prev => ({ ...prev, fontSize: SIZES[currentIndex + 1] }));
    }
  };

  const decreaseFontSize = () => {
    const currentIndex = SIZES.indexOf(prefs.fontSize);
    if (currentIndex > 0) {
      setPrefs(prev => ({ ...prev, fontSize: SIZES[currentIndex - 1] }));
    }
  };

  const resetFontSize = () => setPrefs(prev => ({ ...prev, fontSize: 'medium' }));

  return {
    prefs,
    setPrefs,
    toggleDarkMode,
    toggleHighContrast,
    increaseFontSize,
    decreaseFontSize,
    resetFontSize,
  };
}
