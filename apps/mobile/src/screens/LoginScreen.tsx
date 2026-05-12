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
import { useAuth } from '../contexts/AuthContext'
import { login } from '../services/auth'

interface Props {
  navigation: any
}

export function LoginScreen({ navigation }: Props) {
  const { colors } = useTheme()
  const { setUsuario } = useAuth()
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [carregando, setCarregando] = useState(false)

  async function handleLogin() {
    if (!email || !senha) {
      Alert.alert('Atenção', 'Preencha email e senha')
      return
    }
    setCarregando(true)
    try {
      const response = await login(email, senha)
      setUsuario(response.usuario)
      navigation.replace('Home')
    } catch {
      Alert.alert('Erro', 'Email ou senha inválidos')
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
        <Text style={[styles.logo, { color: colors.primary }]}>Missa Hoje</Text>
        <Text style={[styles.desc, { color: colors.textSecondary }]}>
          Acompanhe a missa diária
        </Text>

        <TextInput
          style={[
            styles.input,
            {
              backgroundColor: colors.surface,
              color: colors.text,
              borderColor: colors.border,
              fontSize: 20,
            },
          ]}
          placeholder="Email"
          placeholderTextColor={colors.textSecondary}
          value={email}
          onChangeText={setEmail}
          keyboardType="email-address"
          autoCapitalize="none"
          accessibilityLabel="Email"
        />

        <TextInput
          style={[
            styles.input,
            {
              backgroundColor: colors.surface,
              color: colors.text,
              borderColor: colors.border,
              fontSize: 20,
            },
          ]}
          placeholder="Senha"
          placeholderTextColor={colors.textSecondary}
          value={senha}
          onChangeText={setSenha}
          secureTextEntry
          accessibilityLabel="Senha"
        />

        <AccessibleButton
          label={carregando ? 'Entrando...' : 'Entrar'}
          onPress={handleLogin}
          disabled={carregando}
          style={styles.button}
        />

        <AccessibleButton
          label="Criar conta"
          onPress={() => navigation.navigate('Cadastro')}
          variant="outline"
          style={styles.button}
        />

        <AccessibleButton
          label="Esqueci minha senha"
          onPress={() => navigation.navigate('RecuperarSenha')}
          variant="secondary"
          style={styles.button}
        />
      </ScrollView>
    </KeyboardAvoidingView>
  )
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scroll: {
    flexGrow: 1,
    justifyContent: 'center',
    padding: 24,
  },
  logo: {
    fontSize: 36,
    fontWeight: '800',
    textAlign: 'center',
    marginBottom: 8,
  },
  desc: {
    fontSize: 18,
    textAlign: 'center',
    marginBottom: 40,
  },
  input: {
    height: 56,
    borderWidth: 1,
    borderRadius: 12,
    paddingHorizontal: 16,
    marginBottom: 16,
    fontSize: 20,
  },
  button: {
    marginTop: 12,
  },
})
