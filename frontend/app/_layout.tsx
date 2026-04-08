import { Stack } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { AuthProvider } from '@/src/AuthContext';

export default function RootLayout() {
  return (
    <AuthProvider>
      <StatusBar style="light" />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: '#0A0A0A' } }}>
        <Stack.Screen name="index" />
        <Stack.Screen name="(auth)" />
        <Stack.Screen name="(tabs)" />
        <Stack.Screen name="server/[id]" options={{ animation: 'slide_from_right' }} />
        <Stack.Screen name="channel/[id]" options={{ animation: 'slide_from_right' }} />
        <Stack.Screen name="dm/[id]" options={{ animation: 'slide_from_right' }} />
        <Stack.Screen name="create-server" options={{ presentation: 'modal', animation: 'slide_from_bottom' }} />
        <Stack.Screen name="join-server" options={{ presentation: 'modal', animation: 'slide_from_bottom' }} />
        <Stack.Screen name="create-channel" options={{ presentation: 'modal', animation: 'slide_from_bottom' }} />
        <Stack.Screen name="settings" options={{ animation: 'slide_from_right' }} />
      </Stack>
    </AuthProvider>
  );
}
