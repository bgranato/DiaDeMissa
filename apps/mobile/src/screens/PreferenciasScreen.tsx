import React from 'react'
import { View, Text, Switch, StyleSheet, ScrollView } from 'react-native'
import { useTheme } from '../contexts/ThemeContext'
import { FontControl } from '../components/FontControl'

export function PreferenciasScreen() {
  const { colors, fontSize, modoEscuro, setModoEscuro, altoContraste, setAltoContraste } = useTheme()

  return (
    <ScrollView style={[styles.container, { backgroundColor: colors.background }]} contentContainerStyle={styles.content}>
      <Text style={[styles.title, { color: colors.text, fontSize: fontSize + 4 }]}>
        Acessibilidade
      </Text>

      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>Tamanho da Fonte</Text>
        <Text style={[styles.sectionDesc, { color: colors.text, fontSize }]}>
          Ajuste o tamanho da fonte para melhor leitura.
        </Text>
        <FontControl />
      </View>

      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>Modo Escuro</Text>
        <View style={styles.row}>
          <Text style={[styles.rowLabel, { color: colors.text, fontSize }]}>Ativar modo escuro</Text>
          <Switch
            value={modoEscuro}
            onValueChange={setModoEscuro}
            accessibilityLabel="Ativar modo escuro"
          />
        </View>
      </View>

      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>Alto Contraste</Text>
        <View style={styles.row}>
          <Text style={[styles.rowLabel, { color: colors.text, fontSize }]}>Ativar alto contraste</Text>
          <Switch
            value={altoContraste}
            onValueChange={setAltoContraste}
            accessibilityLabel="Ativar alto contraste"
          />
        </View>
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 24 },
  title: { fontWeight: '700', marginBottom: 32 },
  section: { marginBottom: 32 },
  sectionTitle: { fontSize: 16, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 },
  sectionDesc: { marginBottom: 12, lineHeight: 28 },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
  },
  rowLabel: { flex: 1 },
})
