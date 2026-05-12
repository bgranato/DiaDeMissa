import React, { useState } from 'react'
import { View, Text, TextInput, StyleSheet, Alert } from 'react-native'
import { AccessibleButton } from '../components/AccessibleButton'
import { useTheme } from '../contexts/ThemeContext'

interface Props {
  navigation: any
}

export function RecuperarSenhaScreen({ navigation }: Props) {
  const { colors } = useTheme()
  const [email, setEmail] = useState('')

  function handleRecuperar() {
    if (!email) {
      Alert.alert('Atenção', 'Informe seu email')
      return
    }
    Alert.alert('Email enviado', 'Se o email estiver cadastrado, você receberá instruções.')
    navigation.goBack()
  }

  return (
    <View style={[styles.container, { backgroundColor: colors.background }]}>
      <Text style={[styles.title, { color: colors.text }]}>Recuperar Senha</Text>
      <Text style={[styles.desc, { color: colors.textSecondary }]}>
        Digite seu email cadastrado para receber instruções.
      </Text>

      <TextInput
        style={[styles.input, { backgroundColor: colors.surface, color: colors.text, borderColor: colors.border, fontSize: 20 }]}
        placeholder="Email"
        placeholderTextColor={colors.textSecondary}
        value={email}
        onChangeText={setEmail}
        keyboardType="email-address"
        autoCapitalize="none"
        accessibilityLabel="Email para recuperação"
      />

      <AccessibleButton label="Enviar" onPress={handleRecuperar} style={styles.button} />
      <AccessibleButton label="Voltar" onPress={() => navigation.goBack()} variant="secondary" style={styles.button} />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, justifyContent: 'center', padding: 24 },
  title: { fontSize: 28, fontWeight: '700', textAlign: 'center', marginBottom: 16 },
  desc: { fontSize: 18, textAlign: 'center', marginBottom: 32 },
  input: { height: 56, borderWidth: 1, borderRadius: 12, paddingHorizontal: 16, marginBottom: 16 },
  button: { marginTop: 12 },
})
