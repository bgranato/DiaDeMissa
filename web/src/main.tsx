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
    // Novo acesso SEMPRE no tamanho padrão ('medium' = 100%), ignorando um valor
    // maior salvo. Tema/contraste seguem persistindo. (O useAccessibility também
    // normaliza a fonte salva para 'medium' ao montar.)
    document.documentElement.style.fontSize = '100%'
    document.documentElement.setAttribute('data-font-size', 'medium')
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
