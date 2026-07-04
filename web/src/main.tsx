import React from 'react'
import ReactDOM from 'react-dom/client'
import { ThemeProvider } from './contexts/ThemeContext'
import { AuthProvider } from './contexts/AuthContext'
import App from './App'
import './index.css'

// Aplica as preferências de acessibilidade salvas ANTES de renderizar, no root.
// Corrige o bug em que o tamanho de fonte (e modos) não era reaplicado ao recarregar
// — o seletor mostrava o valor salvo, mas o texto voltava ao padrão.
;(function aplicarPreferenciasSalvas() {
  try {
    const p = JSON.parse(localStorage.getItem('missa_hoje_prefs') || '{}')
    const mapa: Record<string, string> = {
      small: '90%', medium: '100%', large: '115%', 'extra-large': '130%', huge: '150%',
    }
    if (p.fontSize && mapa[p.fontSize]) {
      document.documentElement.style.fontSize = mapa[p.fontSize]
      document.documentElement.setAttribute('data-font-size', p.fontSize)
    }
    document.documentElement.classList.toggle('dark', !!p.darkMode)
    document.documentElement.classList.toggle('high-contrast', !!p.highContrast)
  } catch { /* preferências ausentes/corrompidas: ignora e usa o padrão */ }
})()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <AuthProvider>
        <App />
      </AuthProvider>
    </ThemeProvider>
  </React.StrictMode>,
)
