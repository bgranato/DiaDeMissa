import React from 'react'
import { NavigationContainer } from '@react-navigation/native'
import { createNativeStackNavigator } from '@react-navigation/native-stack'

import { SplashScreen } from '../screens/SplashScreen'
import { LoginScreen } from '../screens/LoginScreen'
import { CadastroScreen } from '../screens/CadastroScreen'
import { RecuperarSenhaScreen } from '../screens/RecuperarSenhaScreen'
import { HomeScreen } from '../screens/HomeScreen'
import { LeituraMissaScreen } from '../screens/LeituraMissaScreen'
import { IndiceMissaScreen } from '../screens/IndiceMissaScreen'
import { CalendarioScreen } from '../screens/CalendarioScreen'
import { HistoricoScreen } from '../screens/HistoricoScreen'
import { ConfiguracoesScreen } from '../screens/ConfiguracoesScreen'
import { PreferenciasScreen } from '../screens/PreferenciasScreen'
import { AreaUsuarioScreen } from '../screens/AreaUsuarioScreen'
import { LembretesScreen } from '../screens/LembretesScreen'

const Stack = createNativeStackNavigator()

export function AppNavigator() {
  return (
    <NavigationContainer>
      <Stack.Navigator
        initialRouteName="Splash"
        screenOptions={{
          headerShown: false,
          animation: 'slide_from_right',
        }}
      >
        <Stack.Screen name="Splash" component={SplashScreen} />
        <Stack.Screen name="Login" component={LoginScreen} />
        <Stack.Screen name="Cadastro" component={CadastroScreen} />
        <Stack.Screen name="RecuperarSenha" component={RecuperarSenhaScreen} />
        <Stack.Screen name="Home" component={HomeScreen} />
        <Stack.Screen name="LeituraMissa" component={LeituraMissaScreen} />
        <Stack.Screen name="IndiceMissa" component={IndiceMissaScreen} />
        <Stack.Screen name="Calendario" component={CalendarioScreen} />
        <Stack.Screen name="Historico" component={HistoricoScreen} />
        <Stack.Screen name="Configuracoes" component={ConfiguracoesScreen} />
        <Stack.Screen name="Preferencias" component={PreferenciasScreen} />
        <Stack.Screen name="AreaUsuario" component={AreaUsuarioScreen} />
        <Stack.Screen name="Lembretes" component={LembretesScreen} />
      </Stack.Navigator>
    </NavigationContainer>
  )
}
