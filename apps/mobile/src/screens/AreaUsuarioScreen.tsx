import React, { useState } from 'react'
import { View, Text, TextInput, StyleSheet, Alert } from 'react-native'
import { useTheme } from '../contexts/ThemeContext'
import { useAuth } from '../contexts/AuthContext'
import { AccessibleButton } from '../components/AccessibleButton'
import { atualizarUsuario } from '../services/auth'

export function AreaUsuarioScreen() {
  const { colors, fontSize } = useTheme()
  const { usuario, setUsuario } = useAuth()
  const [nome, setNome] = useState(usuario?.nome || '')
  const [email, setEmail] = useState(usuario?.email || '')
  const [carregando, setCarregando] = useState(false)

  async function handleSalvar() {
    if (!nome) {
      Alert.alert('Atenção', 'O nome é obrigatório')
      return
    }
    setCarregando(true)
    try {
      const atualizado = await atualizarUsuario({ nome, email })
      setUsuario(atualizado)
      Alert.alert('Sucesso', 'Dados atualizados')
    } catch {
      Alert.alert('Erro', 'Não foi possível atualizar')
    } finally {
      setCarregando(false)
    }
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Text style={[styles.title, { color: colors.text, fontSize: fontSize + 4 }]}>Meus Dados</Text>

      <TextInput
        style={[styles.input, { backgroundColor: colors.surface, color: colors.text, borderColor: colors.border, fontSize }]}
        placeholder="Nome"
        placeholderTextColor={colors.textSecondary}
        value={nome}
        onChangeText={setNome}
        accessibilityLabel="Nome"
      />

      <TextInput
        style={[styles.input, { backgroundColor: colors.surface, color: colors.text, borderColor: colors.border, fontSize }]}
        placeholder="Email"
        placeholderTextColor={colors.textSecondary}
        value={email}
        onChangeText={setEmail}
        keyboardType="email-address"
        autoCapitalize="none"
        accessibilityLabel="Email"
      />

      <Text style={[styles.info, { color: colors.textSecondary, fontSize: fontSize - 4 }]}>
        Cadastrado via: {usuario?.provider === 'google' ? 'Google' : 'Email'}
      </Text>

      <AccessibleButton
        label={carregando ? 'Salvando...' : 'Salvar'}
        onPress={handleSalvar}
        disabled={carregando}
        style={styles.button}
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, padding: 24 },
  title: { fontWeight: '700', marginBottom: 32 },
  input: { height: 56, borderWidth: 1, borderRadius: 12, paddingHorizontal: 16, marginBottom: 16 },
  info: { marginBottom: 24, fontStyle: 'italic' },
  button: { marginTop: 8 },
})
