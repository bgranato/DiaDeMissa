import React, { useState } from 'react'
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Alert,
} from 'react-native'
import { AccessibleButton } from '../components/AccessibleButton'
import { useTheme } from '../contexts/ThemeContext'
import { cadastrar } from '../services/auth'

interface Props {
  navigation: any
}

export function CadastroScreen({ navigation }: Props) {
  const { colors } = useTheme()
  const [nome, setNome] = useState('')
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [carregando, setCarregando] = useState(false)

  async function handleCadastro() {
    if (!nome || !email || !senha) {
      Alert.alert('Atenção', 'Preencha todos os campos')
      return
    }
    setCarregando(true)
    try {
      await cadastrar(nome, email, senha)
      Alert.alert('Sucesso', 'Conta criada! Faça o login.', [
        { text: 'OK', onPress: () => navigation.goBack() },
      ])
    } catch {
      Alert.alert('Erro', 'Não foi possível criar a conta')
    } finally {
      setCarregando(false)
    }
  }

  return (
    <KeyboardAvoidingView
      style={[styles.container, { backgroundColor: colors.background }]}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
    >
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={[styles.title, { color: colors.text }]}>Criar Conta</Text>

        <TextInput
          style={[styles.input, { backgroundColor: colors.surface, color: colors.text, borderColor: colors.border, fontSize: 20 }]}
          placeholder="Nome completo"
          placeholderTextColor={colors.textSecondary}
          value={nome}
          onChangeText={setNome}
          accessibilityLabel="Nome completo"
        />

        <TextInput
          style={[styles.input, { backgroundColor: colors.surface, color: colors.text, borderColor: colors.border, fontSize: 20 }]}
          placeholder="Email"
          placeholderTextColor={colors.textSecondary}
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
          accessibilityLabel="Email"
        />

        <TextInput
          style={[styles.input, { backgroundColor: colors.surface, color: colors.text, borderColor: colors.border, fontSize: 20 }]}
          placeholder="Senha"
          placeholderTextColor={colors.textSecondary}
          value={senha}
          onChangeText={setSenha}
          secureTextEntry
          accessibilityLabel="Senha"
        />

        <AccessibleButton
          label={carregando ? 'Criando...' : 'Criar conta'}
          onPress={handleCadastro}
          disabled={carregando}
          style={styles.button}
        />

        <AccessibleButton
          label="Voltar"
          onPress={() => navigation.goBack()}
          variant="secondary"
          style={styles.button}
        />
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  scroll: { flexGrow: 1, justifyContent: 'center', padding: 24 },
  title: { fontSize: 28, fontWeight: '700', textAlign: 'center', marginBottom: 32 },
  input: { height: 56, borderWidth: 1, borderRadius: 12, paddingHorizontal: 16, marginBottom: 16 },
  button: { marginTop: 12 },
})
