import React from 'react'
import { View, Text, StyleSheet } from 'react-native'
import { useTheme } from '../contexts/ThemeContext'

interface Props {
  current: number
  total: number
}

export function ProgressBar({ current, total }: Props) {
  const { colors } = useTheme()
  const percent = total > 0 ? (current / total) * 100 : 0

  return (
    <View style={styles.container}>
      <Text
        style={[styles.label, { color: colors.textSecondary }]}
        accessibilityLabel={`Bloco ${current} de ${total}`}
      >
        {current} de {total}
      </Text>
      <View
        style={[styles.track, { backgroundColor: colors.progressBackground }]}
        accessibilityRole="progressbar"
        accessibilityValue={{ min: 0, max: total, now: current }}
      >
        <View
          style={[
            styles.fill,
            { width: `${percent}%`, backgroundColor: colors.progressFill },
          ]}
        />
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    paddingVertical: 8,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 6,
    textAlign: 'center',
  },
  track: {
    height: 8,
    borderRadius: 4,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: 4,
  },
})
