import { useState, useEffect } from 'react';
import { UserPreferences } from '../types/mass';

export function useAccessibility() {
  const [prefs, setPrefs] = useState<UserPreferences>(() => {
    const saved = localStorage.getItem('missa_hoje_prefs');
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
      'extra-large': '130%'
    };
    document.documentElement.style.fontSize = rootFontSizeMap[prefs.fontSize];
    document.documentElement.setAttribute('data-font-size', prefs.fontSize);
  }, [prefs]);

  const toggleDarkMode = () => setPrefs(prev => ({ ...prev, darkMode: !prev.darkMode, highContrast: false }));
  const toggleHighContrast = () => setPrefs(prev => ({ ...prev, highContrast: !prev.highContrast, darkMode: false }));
  
  const increaseFontSize = () => {
    const sizes: UserPreferences['fontSize'][] = ['small', 'medium', 'large', 'extra-large'];
    const currentIndex = sizes.indexOf(prefs.fontSize);
    if (currentIndex < sizes.length - 1) {
      setPrefs(prev => ({ ...prev, fontSize: sizes[currentIndex + 1] }));
    }
  };

  const decreaseFontSize = () => {
    const sizes: UserPreferences['fontSize'][] = ['small', 'medium', 'large', 'extra-large'];
    const currentIndex = sizes.indexOf(prefs.fontSize);
    if (currentIndex > 0) {
      setPrefs(prev => ({ ...prev, fontSize: sizes[currentIndex - 1] }));
    }
  };

  return {
    prefs,
    setPrefs,
    toggleDarkMode,
    toggleHighContrast,
    increaseFontSize,
    decreaseFontSize
  };
}
