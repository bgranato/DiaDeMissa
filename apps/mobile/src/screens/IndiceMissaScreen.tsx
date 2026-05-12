import React, { useEffect, useState } from 'react'
import { View, Text, FlatList, StyleSheet, TouchableOpacity, ActivityIndicator } from 'react-native'
import { useTheme } from '../contexts/ThemeContext'
import { getBlocosMissa } from '../services/missa'
import type { BlocoLiturgico } from '../types/missa'

interface Props {
  route: { params: { missaId: number; blocoId?: number } }
  navigation: any
}

export function IndiceMissaScreen({ route, navigation }: Props) {
  const { missaId, blocoId } = route.params
  const { colors, fontSize } = useTheme()
  const [blocos, setBlocos] = useState<BlocoLiturgico[]>([])
  const [carregando, setCarregando] = useState(true)

  useEffect(() => {
    carregar()
  }, [])

  async function carregar() {
    try {
      const data = await getBlocosMissa(missaId)
      setBlocos(data.filter((b) => b.visivel))
    } catch {
      setBlocos([])
    } finally {
      setCarregando(false)
    }
  }

  function irParaBloco(bloco: BlocoLiturgico) {
    navigation.navigate('LeituraMissa', { missaId, blocoIndex: bloco.ordem - 1 })
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
      <Text style={[styles.title, { color: colors.text, fontSize: fontSize + 4 }]}>Índice da Missa</Text>
      <FlatList
        data={blocos}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={styles.list}
        renderItem={({ item }) => (
          <TouchableOpacity
            onPress={() => irParaBloco(item)}
            accessibilityRole="button"
            accessibilityLabel={`Ir para ${item.titulo}`}
            style={[
              styles.item,
              {
                backgroundColor: colors.surface,
                borderColor: colors.border,
              },
              item.id === blocoId && { borderColor: colors.primary, borderWidth: 2 },
            ]}
          >
            <Text style={[styles.ordem, { color: colors.textSecondary }]}>
              {item.ordem}
            </Text>
            <View style={styles.itemContent}>
              <Text style={[styles.itemTitulo, { color: colors.text, fontSize }]}>{item.titulo}</Text>
              {item.referencia && (
                <Text style={[styles.itemRef, { color: colors.textSecondary, fontSize: fontSize - 4 }]}>
                  {item.referencia}
                </Text>
              )}
            </View>
          </TouchableOpacity>
        )}
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
    marginBottom: 8,
    borderWidth: 1,
    minHeight: 56,
  },
  ordem: {
    fontSize: 18,
    fontWeight: '700',
    width: 36,
    textAlign: 'center',
  },
  itemContent: { flex: 1 },
  itemTitulo: { fontWeight: '600' },
  itemRef: { marginTop: 2 },
})
