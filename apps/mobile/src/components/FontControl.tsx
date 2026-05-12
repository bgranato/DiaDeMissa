import React from 'react'
import { View, TouchableOpacity, Text, StyleSheet } from 'react-native'
import { useTheme } from '../contexts/ThemeContext'

export function FontControl() {
  const { colors, tokens, aumentarFonte, diminuirFonte, fontSize } = useTheme()

  return (
    <View style={[styles.container, { borderColor: colors.border }]}>
      <TouchableOpacity
        onPress={diminuirFonte}
        accessibilityRole="button"
        accessibilityLabel="Diminuir tamanho da fonte"
        style={[styles.button, { minHeight: tokens.touchTargetMin, minWidth: tokens.touchTargetMin }]}
      >
        <Text style={[styles.label, { color: colors.text }]}>A-</Text>
      </TouchableOpacity>
      <Text style={[styles.current, { color: colors.text }]}>{fontSize}</Text>
      <TouchableOpacity
        onPress={aumentarFonte}
        accessibilityRole="button"
        accessibilityLabel="Aumentar tamanho da fonte"
        style={[styles.button, { minHeight: tokens.touchTargetMin, minWidth: tokens.touchTargetMin }]}
      >
        <Text style={[styles.label, { color: colors.text }]}>A+</Text>
      </TouchableOpacity>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: 12,
    overflow: 'hidden',
  },
  button: {
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 12,
  },
  label: {
    fontSize: 22,
    fontWeight: '700',
  },
  current: {
    fontSize: 16,
    fontWeight: '600',
    paddingHorizontal: 8,
  },
})
