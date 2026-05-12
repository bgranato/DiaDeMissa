import React, { useEffect, useState } from 'react'
import { View, Text, FlatList, StyleSheet, TouchableOpacity, ActivityIndicator } from 'react-native'
import { useTheme } from '../contexts/ThemeContext'
import api from '../services/api'
import type { HistoricoEntry } from '../types/usuario'

interface Props {
  navigation: any
}

export function HistoricoScreen({ navigation }: Props) {
  const { colors, fontSize } = useTheme()
  const [historico, setHistorico] = useState<HistoricoEntry[]>([])
  const [carregando, setCarregando] = useState(true)

  useEffect(() => {
    carregar()
  }, [])

  async function carregar() {
    try {
      const response = await api.get<HistoricoEntry[]>('/usuarios/me/historico')
      setHistorico(response.data)
    } catch {
      setHistorico([])
    } finally {
      setCarregando(false)
    }
  }

  function irParaMissa(entry: HistoricoEntry) {
    navigation.navigate('LeituraMissa', { missaId: entry.missa_id })
  }

  if (carregando) {
    return (
      <View style={[styles.loader, { backgroundColor: colors.background }]}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    )
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Text style={[styles.title, { color: colors.text, fontSize: fontSize + 4 }]}>Histórico</Text>
      <FlatList
        data={historico}
        keyExtractor={(item) => String(item.missa_id)}
        contentContainerStyle={styles.list}
        renderItem={({ item }) => (
          <TouchableOpacity
            onPress={() => irParaMissa(item)}
            accessibilityRole="button"
            accessibilityLabel={`Continuar missa de ${item.data}`}
            style={[styles.item, { backgroundColor: colors.surface, borderColor: colors.border }]}
          >
            <Text style={[styles.itemData, { color: colors.primary, fontSize }]}>
              {new Date(item.data + 'T12:00:00').toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric', month: 'long' })}
            </Text>
            <Text style={[styles.itemCelebracao, { color: colors.text, fontSize: fontSize - 2 }]}>
              {item.celebracao || 'Missa'}
            </Text>
            <View style={styles.progressRow}>
              <View style={[styles.progressTrack, { backgroundColor: colors.progressBackground }]}>
                <View style={[styles.progressFill, { width: `${item.percentual_lido}%`, backgroundColor: colors.progressFill }]} />
              </View>
              <Text style={[styles.progressText, { color: colors.textSecondary }]}>
                {Math.round(item.percentual_lido)}%
              </Text>
            </View>
          </TouchableOpacity>
        )}
        ListEmptyComponent={
          <Text style={[styles.empty, { color: colors.textSecondary, fontSize }]}>
            Nenhuma missa acessada ainda.
          </Text>
        }
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  loader: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  title: { fontWeight: '700', textAlign: 'center', padding: 24, paddingBottom: 8 },
  list: { padding: 24, paddingTop: 8 },
  item: {
    padding: 20,
    borderRadius: 12,
    borderWidth: 1,
    marginBottom: 12,
    minHeight: 56,
  },
  itemData: { fontWeight: '700', marginBottom: 4, textTransform: 'capitalize' },
  itemCelebracao: { marginBottom: 12 },
  progressRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  progressTrack: { flex: 1, height: 6, borderRadius: 3 },
  progressFill: { height: '100%', borderRadius: 3 },
  progressText: { fontSize: 14, fontWeight: '600', width: 40, textAlign: 'right' },
  empty: { textAlign: 'center', marginTop: 40 },
})
