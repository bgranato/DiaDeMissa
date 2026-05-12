import React, { useState, useEffect } from 'react'
import { View, Text, StyleSheet, FlatList, TouchableOpacity } from 'react-native'
import { useTheme } from '../contexts/ThemeContext'
import { getMissaPorData } from '../services/missa'
import type { Missa } from '../types/missa'

interface Props {
  navigation: any
}

export function CalendarioScreen({ navigation }: Props) {
  const { colors, fontSize } = useTheme()
  const [missas, setMissas] = useState<Missa[]>([])
  const [ano, setAno] = useState(new Date().getFullYear())
  const [mes, setMes] = useState(new Date().getMonth())

  useEffect(() => {
    carregarMissas()
  }, [ano, mes])

  async function carregarMissas() {
    const diasNoMes = new Date(ano, mes + 1, 0).getDate()
    const resultados: Missa[] = []
    for (let d = 1; d <= Math.min(diasNoMes, 7); d++) {
      try {
        const dataStr = `${ano}-${String(mes + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
        const missa = await getMissaPorData(dataStr)
        resultados.push(missa)
      } catch {
        // ignora dias sem missa
      }
    }
    setMissas(resultados)
  }

  function irParaMissa(missa: Missa) {
    navigation.navigate('LeituraMissa', { missaId: missa.id })
  }

  const meses = [
    'Janeiro', 'Fevereiro', 'Março', 'Abril', 'Maio', 'Junho',
    'Julho', 'Agosto', 'Setembro', 'Outubro', 'Novembro', 'Dezembro',
  ]

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => {
            if (mes === 0) { setMes(11); setAno(ano - 1) } else { setMes(mes - 1) }
          }}
          accessibilityLabel="Mês anterior"
          style={styles.arrow}
        >
          <Text style={[styles.arrowText, { color: colors.primary }]}>◀</Text>
        </TouchableOpacity>
        <Text style={[styles.mesText, { color: colors.text, fontSize: fontSize + 2 }]}>
          {meses[mes]} {ano}
        </Text>
        <TouchableOpacity
          onPress={() => {
            if (mes === 11) { setMes(0); setAno(ano + 1) } else { setMes(mes + 1) }
          }}
          accessibilityLabel="Próximo mês"
          style={styles.arrow}
        >
          <Text style={[styles.arrowText, { color: colors.primary }]}>▶</Text>
        </TouchableOpacity>
      </View>

      <FlatList
        data={missas}
        keyExtractor={(item) => String(item.id)}
        contentContainerStyle={styles.list}
        renderItem={({ item }) => (
          <TouchableOpacity
            onPress={() => irParaMissa(item)}
            accessibilityRole="button"
            accessibilityLabel={`Missa de ${item.data}`}
            style={[styles.item, { backgroundColor: colors.surface, borderColor: colors.border }]}
          >
            <Text style={[styles.itemData, { color: colors.primary, fontSize }]}>
              {new Date(item.data + 'T12:00:00').toLocaleDateString('pt-BR', { weekday: 'long', day: 'numeric' })}
            </Text>
            <Text style={[styles.itemCelebracao, { color: colors.text, fontSize: fontSize - 2 }]}>
              {item.celebracao || 'Missa'}
            </Text>
          </TouchableOpacity>
        )}
        ListEmptyComponent={
          <Text style={[styles.empty, { color: colors.textSecondary, fontSize }]}>
            Nenhuma missa encontrada para este mês.
          </Text>
        }
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: 24,
    paddingBottom: 8,
  },
  mesText: { fontWeight: '700' },
  arrow: { padding: 16, minWidth: 48, alignItems: 'center' },
  arrowText: { fontSize: 24 },
  list: { padding: 24, paddingTop: 8 },
  item: {
    padding: 20,
    borderRadius: 12,
    borderWidth: 1,
    marginBottom: 12,
    minHeight: 56,
  },
  itemData: { fontWeight: '700', marginBottom: 4, textTransform: 'capitalize' },
  itemCelebracao: {},
  empty: { textAlign: 'center', marginTop: 40 },
})
