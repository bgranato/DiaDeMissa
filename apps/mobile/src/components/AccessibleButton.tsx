import React from 'react'
import {
  TouchableOpacity,
  Text,
  StyleSheet,
  ViewStyle,
  TextStyle,
} from 'react-native'
import { useTheme } from '../contexts/ThemeContext'

interface Props {
  label: string
  accessibilityLabel?: string
  onPress: () => void
  variant?: 'primary' | 'secondary' | 'outline'
  size?: 'large' | 'small'
  disabled?: boolean
  style?: ViewStyle
}

export function AccessibleButton({
  label,
  accessibilityLabel,
  onPress,
  variant = 'primary',
  size = 'large',
  disabled = false,
  style,
}: Props) {
  const { colors, tokens } = useTheme()

  const buttonHeight = size === 'large' ? tokens.buttonMinHeight : 44
  const fontSize = size === 'large' ? 20 : 16

  const buttonStyle: ViewStyle = {
    height: buttonHeight,
    borderRadius: 12,
    justifyContent: 'center' as const,
    alignItems: 'center' as const,
    paddingHorizontal: tokens.spacingDefault,
    opacity: disabled ? 0.5 : 1,
  }

  const textStyle: TextStyle = {
    fontSize,
    fontWeight: '700' as const,
  }

  if (variant === 'primary') {
    buttonStyle.backgroundColor = colors.primary
    textStyle.color = colors.primaryText
  } else if (variant === 'secondary') {
    buttonStyle.backgroundColor = colors.surface
    textStyle.color = colors.text
  } else {
    buttonStyle.backgroundColor = 'transparent'
    buttonStyle.borderWidth = 2
    buttonStyle.borderColor = colors.primary
    textStyle.color = colors.primary
  }

  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled}
      accessibilityRole="button"
      accessibilityLabel={accessibilityLabel || label}
      accessibilityState={{ disabled }}
      style={[buttonStyle, style]}
    >
      <Text style={textStyle}>{label}</Text>
    </TouchableOpacity>
  )
}
