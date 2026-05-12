export interface ThemeTokens {
  fontSizeMin: number
  fontSizeDefault: number
  fontSizeMax: number
  lineHeightDefault: number
  buttonMinHeight: number
  touchTargetMin: number
  spacingDefault: number
}

export const baseTokens: ThemeTokens = {
  fontSizeMin: 14,
  fontSizeDefault: 20,
  fontSizeMax: 28,
  lineHeightDefault: 1.6,
  buttonMinHeight: 56,
  touchTargetMin: 48,
  spacingDefault: 24,
}

export interface ThemeColors {
  background: string
  surface: string
  text: string
  textSecondary: string
  primary: string
  primaryText: string
  border: string
  error: string
  success: string
  progressBackground: string
  progressFill: string
}

export const lightColors: ThemeColors = {
  background: '#FFFFFF',
  surface: '#F5F5F5',
  text: '#1A1A1A',
  textSecondary: '#666666',
  primary: '#1A4B8C',
  primaryText: '#FFFFFF',
  border: '#E0E0E0',
  error: '#D32F2F',
  success: '#388E3C',
  progressBackground: '#E0E0E0',
  progressFill: '#1A4B8C',
}

export const darkColors: ThemeColors = {
  background: '#000000',
  surface: '#1A1A1A',
  text: '#FFFFFF',
  textSecondary: '#CCCCCC',
  primary: '#4A90D9',
  primaryText: '#000000',
  border: '#333333',
  error: '#EF5350',
  success: '#66BB6A',
  progressBackground: '#333333',
  progressFill: '#4A90D9',
}

export const highContrastColors: ThemeColors = {
  background: '#FFFFFF',
  surface: '#FFFFFF',
  text: '#000000',
  textSecondary: '#000000',
  primary: '#0000FF',
  primaryText: '#FFFFFF',
  border: '#000000',
  error: '#CC0000',
  success: '#006600',
  progressBackground: '#CCCCCC',
  progressFill: '#000000',
}

export const highContrastDarkColors: ThemeColors = {
  background: '#000000',
  surface: '#000000',
  text: '#FFFFFF',
  textSecondary: '#FFFFFF',
  primary: '#FFFF00',
  primaryText: '#000000',
  border: '#FFFFFF',
  error: '#FF4444',
  success: '#44FF44',
  progressBackground: '#333333',
  progressFill: '#FFFFFF',
}
