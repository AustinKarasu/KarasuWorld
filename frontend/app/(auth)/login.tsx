import React, { useState } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet,
  KeyboardAvoidingView, Platform, ScrollView, ActivityIndicator,
} from 'react-native';
import { useRouter } from 'expo-router';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import { useAuth } from '@/src/AuthContext';
import { Colors } from '@/src/colors';

export default function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const { login } = useAuth();
  const router = useRouter();

  const handleLogin = async () => {
    if (!email.trim() || !password.trim()) { setError('Please fill in all fields'); return; }
    setError(''); setLoading(true);
    try {
      await login(email, password);
      router.replace('/(tabs)');
    } catch (e: any) {
      setError(e.message || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <SafeAreaView style={styles.safe}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.flex}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <View style={styles.header}>
            <View style={styles.logoContainer}>
              <Ionicons name="planet" size={48} color={Colors.primary} />
            </View>
            <Text style={styles.title}>KarasuWorld</Text>
            <Text style={styles.subtitle}>Welcome back! Sign in to continue</Text>
          </View>

          {error ? (
            <View style={styles.errorBox}>
              <Ionicons name="alert-circle" size={16} color={Colors.error} />
              <Text style={styles.errorText}>{error}</Text>
            </View>
          ) : null}

          <View style={styles.form}>
            <Text style={styles.label}>EMAIL</Text>
            <TextInput testID="login-email-input" style={styles.input} value={email} onChangeText={setEmail} placeholder="you@example.com" placeholderTextColor={Colors.text_tertiary} keyboardType="email-address" autoCapitalize="none" autoCorrect={false} />

            <Text style={styles.label}>PASSWORD</Text>
            <View style={styles.passwordContainer}>
              <TextInput testID="login-password-input" style={styles.passwordInput} value={password} onChangeText={setPassword} placeholder="Enter your password" placeholderTextColor={Colors.text_tertiary} secureTextEntry={!showPassword} autoCapitalize="none" />
              <TouchableOpacity onPress={() => setShowPassword(!showPassword)} style={styles.eyeBtn}>
                <Ionicons name={showPassword ? 'eye-off' : 'eye'} size={20} color={Colors.text_tertiary} />
              </TouchableOpacity>
            </View>

            <TouchableOpacity testID="login-submit-btn" style={[styles.button, loading && styles.buttonDisabled]} onPress={handleLogin} disabled={loading} activeOpacity={0.8}>
              {loading ? <ActivityIndicator color="#FFF" size="small" /> : <Text style={styles.buttonText}>Sign In</Text>}
            </TouchableOpacity>

          </View>

          <View style={styles.footer}>
            <Text style={styles.footerText}>Don&apos;t have an account? </Text>
            <TouchableOpacity testID="go-to-register-btn" onPress={() => router.push('/(auth)/register')}>
              <Text style={styles.footerLink}>Sign Up</Text>
            </TouchableOpacity>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: Colors.bg_primary },
  flex: { flex: 1 },
  scroll: { flexGrow: 1, justifyContent: 'center', padding: 24 },
  header: { alignItems: 'center', marginBottom: 40 },
  logoContainer: { width: 80, height: 80, borderRadius: 20, backgroundColor: Colors.bg_tertiary, justifyContent: 'center', alignItems: 'center', marginBottom: 16, borderWidth: 1, borderColor: Colors.border },
  title: { fontSize: 32, fontWeight: '900', color: Colors.text_primary, letterSpacing: -0.5 },
  subtitle: { fontSize: 15, color: Colors.text_secondary, marginTop: 8 },
  form: { gap: 4 },
  label: { fontSize: 11, fontWeight: '700', color: Colors.text_secondary, letterSpacing: 1, marginBottom: 6, marginTop: 16 },
  input: { backgroundColor: Colors.bg_secondary, borderWidth: 1, borderColor: Colors.border, borderRadius: 8, padding: 14, color: Colors.text_primary, fontSize: 15 },
  passwordContainer: { flexDirection: 'row', alignItems: 'center', backgroundColor: Colors.bg_secondary, borderWidth: 1, borderColor: Colors.border, borderRadius: 8 },
  passwordInput: { flex: 1, padding: 14, color: Colors.text_primary, fontSize: 15 },
  eyeBtn: { padding: 14 },
  button: { backgroundColor: Colors.primary, borderRadius: 8, padding: 16, alignItems: 'center', marginTop: 24 },
  buttonDisabled: { opacity: 0.6 },
  buttonText: { color: '#FFF', fontSize: 16, fontWeight: '700' },
  errorBox: { flexDirection: 'row', alignItems: 'center', gap: 8, backgroundColor: 'rgba(255,59,48,0.1)', borderRadius: 8, padding: 12, marginBottom: 8 },
  errorText: { color: Colors.error, fontSize: 13, flex: 1 },
  footer: { flexDirection: 'row', justifyContent: 'center', marginTop: 32 },
  footerText: { color: Colors.text_secondary, fontSize: 14 },
  footerLink: { color: Colors.primary, fontSize: 14, fontWeight: '700' },
});
