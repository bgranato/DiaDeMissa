import React, { useEffect, useState } from 'react'
import { View, Text, ScrollView, StyleSheet, ActivityIndicator } from 'react-native'
import { useTheme } from '../contexts/ThemeContext'
import { AccessibleButton } from '../components/AccessibleButton'
import { ProgressBar } from '../components/ProgressBar'
import { FontControl } from '../components/FontControl'
import { getBlocosMissa } from '../services/missa'
import type { BlocoLiturgico } from '../types/missa'

interface Props {
  route: { params: { missaId: number } }
  navigation: any
}

export function LeituraMissaScreen({ route, navigation }: Props) {
  const { missaId } = route.params
  const { colors, fontSize, tokens } = useTheme()
  const [blocos, setBlocos] = useState<BlocoLiturgico[]>([])
  const [indice, setIndice] = useState(0)
  const [carregando, setCarregando] = useState(true)

  useEffect(() => {
    carregarBlocos()
  }, [])

  async function carregarBlocos() {
    try {
      const data = await getBlocosMissa(missaId)
      setBlocos(data.filter((b) => b.visivel))
    } catch {
      setBlocos([])
    } finally {
      setCarregando(false)
    }
  }

  const blocoAtual = blocos[indice]
  const podeAvancar = indice < blocos.length - 1
  const podeVoltar = indice > 0

  function avancar() {
    if (podeAvancar) setIndice(indice + 1)
  }

  function voltar() {
    if (podeVoltar) setIndice(indice - 1)
  }

  if (carregando) {
    return (
      <View style={[styles.loaderContainer, { backgroundColor: colors.background }]}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    )
  }

  if (!blocoAtual) {
    return (
      <View style={[styles.loaderContainer, { backgroundColor: colors.background }]}>
        <Text style={[styles.emptyText, { color: colors.textSecondary }]}>
          Nenhum bloco disponível
        </Text>
        <AccessibleButton label="Voltar" onPress={() => navigation.goBack()} variant="outline" />
      </View>
    )
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <View style={styles.topControls}>
        <FontControl />
        <AccessibleButton
          label="Índice"
          onPress={() => navigation.navigate('IndiceMissa', { missaId, blocoId: blocoAtual.id })}
          variant="secondary"
          size="small"
        />
      </View>

      <ProgressBar current={indice + 1} total={blocos.length} />

      <ScrollView
        style={styles.content}
        contentContainerStyle={styles.contentInner}
        showsVerticalScrollIndicator={false}
      >
        <Text
          style={[styles.titulo, { color: colors.primary, fontSize: fontSize + 4 }]}
          accessibilityRole="header"
        >
          {blocoAtual.titulo}
        </Text>

        {blocoAtual.referencia && (
          <Text style={[styles.referencia, { color: colors.textSecondary, fontSize: fontSize - 2 }]}>
            {blocoAtual.referencia}
          </Text>
        )}

        {blocoAtual.conteudo && (
          <Text
            style={[
              styles.conteudo,
              { color: colors.text, fontSize, lineHeight: fontSize * tokens.lineHeightDefault },
            ]}
          >
            {blocoAtual.conteudo}
          </Text>
        )}
      </ScrollView>

      <View style={styles.navigation}>
        <AccessibleButton
          label="Anterior"
          onPress={voltar}
          disabled={!podeVoltar}
          variant="secondary"
          style={styles.navButton}
        />
        {podeAvancar ? (
          <AccessibleButton label="Próximo" onPress={avancar} style={styles.navButton} />
        ) : (
          <AccessibleButton
            label="Concluir"
            onPress={() => navigation.goBack()}
            style={styles.navButton}
          />
        )}
      </View>
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  loaderContainer: { flex: 1, justifyContent: 'center', alignItems: 'center' },
  emptyText: { fontSize: 18, marginBottom: 16 },
  topControls: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingTop: 16,
    paddingBottom: 8,
  },
  content: { flex: 1, paddingHorizontal: 24 },
  contentInner: { paddingBottom: 24 },
  titulo: { fontWeight: '700', marginBottom: 8, marginTop: 16 },
  referencia: { fontWeight: '600', marginBottom: 16, fontStyle: 'italic' },
  conteudo: { fontWeight: '400' },
  navigation: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 24,
    gap: 12,
  },
  navButton: { flex: 1 },
})
