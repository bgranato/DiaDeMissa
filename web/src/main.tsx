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
    // Novo acesso (carga de página) SEMPRE começa no tamanho padrão. O reset é
    // feito UMA VEZ aqui, no boot, e ESCRITO no localStorage — assim os hooks
    // (useAccessibility/ThemeContext) inicializam já resetados. DENTRO da sessão
    // o ajuste é mantido normalmente (os hooks leem o localStorage, que passa a
    // guardar o valor aumentado até a próxima carga de página).
    p.fontSize = 'medium'
    localStorage.setItem('missa_hoje_prefs', JSON.stringify(p))
    localStorage.setItem('@missa_hoje_font', '20')
    document.documentElement.style.fontSize = '100%'
    document.documentElement.setAttribute('data-font-size', 'medium')
    document.documentElement.style.setProperty('--font-size', '20px')
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
