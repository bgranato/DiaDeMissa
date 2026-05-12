import React, { useEffect, useState } from 'react'
import { View, Text, StyleSheet, ScrollView, ActivityIndicator, Alert } from 'react-native'
import { useTheme } from '../contexts/ThemeContext'
import { useAuth } from '../contexts/AuthContext'
import { AccessibleButton } from '../components/AccessibleButton'
import { FontControl } from '../components/FontControl'
import { getMissaHoje } from '../services/missa'
import type { Missa } from '../types/missa'

interface Props {
  navigation: any
}

export function HomeScreen({ navigation }: Props) {
  const { colors, fontSize } = useTheme()
  const { usuario, logout } = useAuth()
  const [missaHoje, setMissaHoje] = useState<Missa | null>(null)
  const [carregando, setCarregando] = useState(true)

  useEffect(() => {
    carregarMissa()
  }, [])

  async function carregarMissa() {
    setCarregando(true)
    try {
      const missa = await getMissaHoje()
      setMissaHoje(missa)
    } catch {
      setMissaHoje(null)
    } finally {
      setCarregando(false)
    }
  }

  function iniciarLeitura() {
    if (missaHoje) {
      navigation.navigate('LeituraMissa', { missaId: missaHoje.id })
    }
  }

  return (
    <ScrollView
      style={[styles.container, { backgroundColor: colors.background }]}
      contentContainerStyle={styles.content}
    >
      <View style={styles.topBar}>
        <Text style={[styles.greeting, { color: colors.text, fontSize }]}>
          Olá, {usuario?.nome?.split(' ')[0] || 'Fiel'}
        </Text>
        <FontControl />
      </View>

      {carregando ? (
        <ActivityIndicator size="large" color={colors.primary} style={styles.loader} />
      ) : missaHoje ? (
        <View style={styles.missaCard}>
          <Text style={[styles.dayLabel, { color: colors.textSecondary }]}>
            Missa de hoje
          </Text>
          <Text style={[styles.celebracao, { color: colors.text, fontSize: fontSize + 4 }]}>
            {missaHoje.celebracao || 'Missa do Dia'}
          </Text>
          <Text style={[styles.data, { color: colors.textSecondary, fontSize: fontSize - 2 }]}>
            {missaHoje.data}
          </Text>
          {missaHoje.tempo_liturgico && (
            <Text style={[styles.tempo, { color: colors.primary, fontSize: fontSize - 2 }]}>
              {missaHoje.tempo_liturgico}
            </Text>
          )}

          <AccessibleButton
            label="Começar"
            onPress={iniciarLeitura}
            style={styles.startButton}
          />

          <AccessibleButton
            label="Ver índice"
            onPress={() => navigation.navigate('IndiceMissa', { missaId: missaHoje.id })}
            variant="outline"
            style={styles.indexButton}
          />
        </View>
      ) : (
        <View style={styles.emptyCard}>
          <Text style={[styles.emptyText, { color: colors.textSecondary, fontSize }]}>
            A missa de hoje ainda não está disponível.
          </Text>
          <AccessibleButton label="Tentar novamente" onPress={carregarMissa} variant="outline" />
        </View>
      )}

      <View style={styles.quickActions}>
        <AccessibleButton
          label="Calendário"
          onPress={() => navigation.navigate('Calendario')}
          variant="secondary"
          size="small"
          style={styles.quickButton}
        />
        <AccessibleButton
          label="Histórico"
          onPress={() => navigation.navigate('Historico')}
          variant="secondary"
          size="small"
          style={styles.quickButton}
        />
        <AccessibleButton
          label="Config"
          onPress={() => navigation.navigate('Configuracoes')}
          variant="secondary"
          size="small"
          style={styles.quickButton}
        />
      </View>

      <AccessibleButton
        label="Sair"
        onPress={logout}
        variant="secondary"
        style={styles.logoutButton}
      />
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 24, paddingBottom: 40 },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 32,
  },
  greeting: { fontWeight: '600' },
  loader: { marginTop: 60 },
  missaCard: {
    alignItems: 'center',
    paddingVertical: 32,
    paddingHorizontal: 24,
    borderRadius: 16,
    marginBottom: 24,
  },
  dayLabel: { fontSize: 16, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 1 },
  celebracao: { fontWeight: '700', textAlign: 'center', marginTop: 12, marginBottom: 8 },
  data: { marginBottom: 4 },
  tempo: { fontWeight: '600', marginBottom: 24 },
  startButton: { width: '100%', marginTop: 8 },
  indexButton: { width: '100%', marginTop: 12 },
  emptyCard: { alignItems: 'center', padding: 32, gap: 16 },
  emptyText: { textAlign: 'center' },
  quickActions: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 12,
    marginTop: 24,
    flexWrap: 'wrap',
  },
  quickButton: { flex: 1, minWidth: 100 },
  logoutButton: { marginTop: 24 },
})
