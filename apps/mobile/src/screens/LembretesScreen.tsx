import React, { useEffect, useState } from 'react'
import { View, Text, FlatList, StyleSheet, TouchableOpacity, ActivityIndicator, Alert } from 'react-native'
import { useTheme } from '../contexts/ThemeContext'
import { AccessibleButton } from '../components/AccessibleButton'
import api from '../services/api'
import type { Lembrete } from '../types/usuario'

export function LembretesScreen() {
  const { colors, fontSize } = useTheme()
  const [lembretes, setLembretes] = useState<Lembrete[]>([])
  const [carregando, setCarregando] = useState(true)

  useEffect(() => {
    carregar()
  }, [])

  async function carregar() {
    try {
      const response = await api.get<Lembrete[]>('/usuarios/me/lembretes')
      setLembretes(response.data)
    } catch {
      setLembretes([])
    } finally {
      setCarregando(false)
    }
  }

  async function deletar(id: number) {
    Alert.alert('Remover lembrete', 'Tem certeza?', [
      { text: 'Cancelar', style: 'cancel' },
      {
        text: 'Remover',
        style: 'destructive',
        onPress: async () => {
          try {
            await api.delete(`/usuarios/me/lembretes/${id}`)
            setLembretes((prev) => prev.filter((l) => l.id !== id))
          } catch {
            Alert.alert('Erro', 'Não foi possível remover')
          }
        },
      },
    ])
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
      <Text style={[styles.title, { color: colors.text, fontSize: fontSize + 4 }]}>Lembretes</Text>

      <FlatList
        data={lembretes}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={styles.list}
        renderItem={({ item }) => (
          <View style={[styles.item, { backgroundColor: colors.surface, borderColor: colors.border }]}>
            <View style={styles.itemContent}>
              <Text style={[styles.itemTitle, { color: colors.text, fontSize }]}>{item.titulo}</Text>
              <Text style={[styles.itemDate, { color: colors.textSecondary, fontSize: fontSize - 4 }]}>
                {new Date(item.data_hora_alerta).toLocaleDateString('pt-BR', {
                  weekday: 'long', day: 'numeric', month: 'long', hour: '2-digit', minute: '2-digit',
                })}
              </Text>
            </View>
            <TouchableOpacity
              onPress={() => deletar(item.id)}
              accessibilityLabel={`Remover lembrete ${item.titulo}`}
              style={styles.deleteButton}
            >
              <Text style={[styles.deleteText, { color: colors.error }]}>Remover</Text>
            </TouchableOpacity>
          </View>
        )}
        ListEmptyComponent={
          <Text style={[styles.empty, { color: colors.textSecondary, fontSize }]}>
            Nenhum lembrete cadastrado.
          </Text>
        }
      />

      <AccessibleButton
        label="Novo lembrete"
        onPress={() => Alert.alert('Em breve', 'Funcionalidade em desenvolvimento')}
        style={styles.addButton}
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
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    borderRadius: 12,
    borderWidth: 1,
    marginBottom: 12,
  },
  itemContent: { flex: 1 },
  itemTitle: { fontWeight: '600', marginBottom: 4 },
  itemDate: { textTransform: 'capitalize' },
  deleteButton: { padding: 12, minWidth: 48, alignItems: 'center' },
  deleteText: { fontSize: 16, fontWeight: '600' },
  empty: { textAlign: 'center', marginTop: 40 },
  addButton: { margin: 24 },
})
