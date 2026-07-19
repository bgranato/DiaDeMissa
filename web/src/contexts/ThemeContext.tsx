import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

interface ThemeContextData {
  fontSize: number
  modoEscuro: boolean
  altoContraste: boolean
  setModoEscuro: (v: boolean) => void
  setAltoContraste: (v: boolean) => void
  aumentarFonte: () => void
  diminuirFonte: () => void
}

const ThemeContext = createContext<ThemeContextData>({} as ThemeContextData)

export function ThemeProvider({ children }: { children: ReactNode }) {
  // Novo acesso SEMPRE começa no tamanho de fonte padrão (20px), mesmo que a
  // pessoa tenha aumentado antes. (Tema/contraste seguem persistindo abaixo.)
  const [fontSize, setFontSize] = useState(20)
  const [modoEscuro, setModoEscuroState] = useState(() => localStorage.getItem('@missa_hoje_dark') === 'true')
  const [altoContraste, setAltoContrasteState] = useState(() => localStorage.getItem('@missa_hoje_contrast') === 'true')

  const syncTheme = useCallback((dark: boolean, contrast: boolean) => {
    document.documentElement.classList.toggle('dark', dark)
    document.documentElement.classList.toggle('high-contrast', contrast)
    localStorage.setItem('@missa_hoje_dark', String(dark))
    localStorage.setItem('@missa_hoje_contrast', String(contrast))
  }, [])

  const setModoEscuro = useCallback((v: boolean) => {
    setModoEscuroState(v); syncTheme(v, altoContraste)
  }, [altoContraste, syncTheme])

  const setAltoContraste = useCallback((v: boolean) => {
    setAltoContrasteState(v); syncTheme(modoEscuro, v)
  }, [modoEscuro, syncTheme])

  const aumentarFonte = useCallback(() => {
    setFontSize(prev => {
      const next = Math.min(prev + 2, 28)
      localStorage.setItem('@missa_hoje_font', String(next))
      document.documentElement.style.setProperty('--font-size', `${next}px`)
      return next
    })
  }, [])

  const diminuirFonte = useCallback(() => {
    setFontSize(prev => {
      const next = Math.max(prev - 2, 14)
      localStorage.setItem('@missa_hoje_font', String(next))
      document.documentElement.style.setProperty('--font-size', `${next}px`)
      return next
    })
  }, [])

  document.documentElement.style.setProperty('--font-size', `${fontSize}px`)

  return (
    <ThemeContext.Provider value={{ fontSize, modoEscuro, altoContraste, setModoEscuro, setAltoContraste, aumentarFonte, diminuirFonte }}>
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  return useContext(ThemeContext)
}
