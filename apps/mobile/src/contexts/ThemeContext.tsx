import React, { createContext, useContext, useState, useMemo } from 'react'
import {
  baseTokens,
  lightColors,
  darkColors,
  highContrastColors,
  highContrastDarkColors,
} from '../theme'
import type { ThemeColors, ThemeTokens } from '../theme'

interface ThemeContextData {
  colors: ThemeColors
  tokens: ThemeTokens
  fontSize: number
  modoEscuro: boolean
  altoContraste: boolean
  setModoEscuro: (v: boolean) => void
  setAltoContraste: (v: boolean) => void
  aumentarFonte: () => void
  diminuirFonte: () => void
}

const ThemeContext = createContext<ThemeContextData>({} as ThemeContextData)

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [modoEscuro, setModoEscuro] = useState(false)
  const [altoContraste, setAltoContraste] = useState(false)
  const [fontSize, setFontSize] = useState(baseTokens.fontSizeDefault)

  const colors = useMemo(() => {
    if (altoContraste && modoEscuro) return highContrastDarkColors
    if (altoContraste) return highContrastColors
    if (modoEscuro) return darkColors
    return lightColors
  }, [modoEscuro, altoContraste])

  const aumentarFonte = () => {
    setFontSize((prev) => Math.min(prev + 2, baseTokens.fontSizeMax))
  }

  const diminuirFonte = () => {
    setFontSize((prev) => Math.max(prev - 2, baseTokens.fontSizeMin))
  }

  return (
    <ThemeContext.Provider
      value={{
        colors,
        tokens: baseTokens,
        fontSize,
        modoEscuro,
        altoContraste,
        setModoEscuro,
        setAltoContraste,
        aumentarFonte,
        diminuirFonte,
      }}
    >
      {children}
    </ThemeContext.Provider>
  )
}

export function useTheme() {
  return useContext(ThemeContext)
}
