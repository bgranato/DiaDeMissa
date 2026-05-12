import React from 'react'
import { View, Text, StyleSheet, ScrollView } from 'react-native'
import { useTheme } from '../contexts/ThemeContext'
import { AccessibleButton } from '../components/AccessibleButton'
import { useAuth } from '../contexts/AuthContext'

interface Props {
  navigation: any
}

export function ConfiguracoesScreen({ navigation }: Props) {
  const { colors, fontSize } = useTheme()
  const { usuario } = useAuth()

  return (
    <ScrollView style={[styles.container, { backgroundColor: colors.background }]} contentContainerStyle={styles.content}>
      <Text style={[styles.title, { color: colors.text, fontSize: fontSize + 4 }]}>Configurações</Text>

      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>Conta</Text>
        <AccessibleButton
          label={`${usuario?.nome || 'Usuário'}`}
          onPress={() => navigation.navigate('AreaUsuario')}
          variant="secondary"
          style={styles.menuItem}
        />
      </View>

      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>Aparência</Text>
        <AccessibleButton
          label="Preferências de Acessibilidade"
          onPress={() => navigation.navigate('Preferencias')}
          variant="secondary"
          style={styles.menuItem}
        />
      </View>

      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>Lembretes</Text>
        <AccessibleButton
          label="Gerenciar lembretes"
          onPress={() => navigation.navigate('Lembretes')}
          variant="secondary"
          style={styles.menuItem}
        />
      </View>

      <View style={styles.section}>
        <Text style={[styles.sectionTitle, { color: colors.textSecondary }]}>Sobre</Text>
        <Text style={[styles.about, { color: colors.text, fontSize }]}>
          Missa Hoje v1.0.0{'\n'}
          Uma alternativa digital acessível ao folheto litúrgico.
        </Text>
      </View>
    </ScrollView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  content: { padding: 24, paddingBottom: 40 },
  title: { fontWeight: '700', textAlign: 'center', marginBottom: 32 },
  section: { marginBottom: 24 },
  sectionTitle: { fontSize: 16, fontWeight: '600', textTransform: 'uppercase', letterSpacing: 1, marginBottom: 8 },
  menuItem: { marginBottom: 8 },
  about: { lineHeight: 28 },
})
