import React, { useEffect } from 'react'
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'

interface Props {
  navigation: any
}

export function SplashScreen({ navigation }: Props) {
  const { estaAutenticado, estaCarregando } = useAuth()
  const { colors } = useTheme()

  useEffect(() => {
    if (!estaCarregando) {
      if (estaAutenticado) {
        navigation.replace('Home')
      } else {
        navigation.replace('Login')
      }
    }
  }, [estaCarregando, estaAutenticado, navigation])

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Text style={[styles.title, { color: colors.primary }]}>Missa Hoje</Text>
      <Text style={[styles.subtitle, { color: colors.textSecondary }]}>
        Acompanhe a missa diária
      </Text>
      <ActivityIndicator size="large" color={colors.primary} style={styles.loader} />
    </View>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 24,
  },
  title: {
    fontSize: 40,
    fontWeight: '800',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 20,
    fontWeight: '400',
  },
  loader: {
    marginTop: 40,
  },
})
